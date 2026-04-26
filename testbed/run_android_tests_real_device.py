#!/usr/bin/env python3
"""Run Android integration tests."""

import argparse
import contextlib
import dataclasses
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
from collections.abc import Generator
from pathlib import Path

import serial  # pyright: ignore[reportMissingTypeStubs]

PREFIX = "[run-android-tests]"


def log(msg: str) -> None:
    print(f"{PREFIX} {msg}", flush=True)


class ADB:
    def __init__(self, device_id: str | None = None):
        self.adb_executable = self._find_adb_executable()

    def _find_adb_executable(self) -> Path:
        """Find adb: prefer ANDROID_HOME/platform-tools, fallback to PATH."""
        android_home = os.environ.get("ANDROID_HOME", "")
        if android_home:
            candidate = (
                Path(android_home)
                / "platform-tools"
                / ("adb.exe" if sys.platform.startswith("win") else "adb")
            )
            if candidate.exists() and os.access(candidate, os.X_OK):
                return candidate
        adb_in_path = shutil.which("adb")
        if adb_in_path:
            return Path(adb_in_path)
        raise FileNotFoundError(
            "adb not found in ANDROID_HOME/platform-tools nor in PATH"
        )

    def call_adb(self, command: list[str]) -> str:
        try:
            result = subprocess.run(
                [str(self.adb_executable)] + command,
                check=True,
                capture_output=True,
                text=True,
            )
            output = result.stdout.strip()
            return output
        except subprocess.CalledProcessError as exc:
            error_output = exc.stderr or exc.stdout or str(exc)
            raise Exception(f"ADB command failed: {error_output}") from exc


# ---------------------------------------------------------------------------
# Serial-to-TCP bridge
# ---------------------------------------------------------------------------
DEVICE_PORT = 9001

_DEFAULT_SERIAL_SPEED = 1_000_000
_DEFAULT_SERIAL_DELAY = 0.5  # same as bumble's DEFAULT_POST_OPEN_DELAY


@dataclasses.dataclass
class SerialMoniker:
    device: str
    speed: int = _DEFAULT_SERIAL_SPEED
    rtscts: bool = False
    dsrdtr: bool = False
    delay: float = 0.0


def parse_serial_moniker(moniker: str) -> SerialMoniker:
    """Parse a Bumble serial transport moniker.

    Format: serial:<device-path>[,<speed>][,rtscts][,dsrdtr][,delay]
    See: https://google.github.io/bumble/transports/serial.html

    Returns a SerialMoniker dataclass.
    """
    if not moniker.startswith("serial:"):
        raise ValueError(
            f"Only serial transport monikers are supported "
            f"(e.g. 'serial:/dev/ttyUSB0,1000000'). Got: {moniker!r}"
        )
    spec = moniker[len("serial:") :]
    if not spec:
        raise ValueError("serial moniker must specify a device path")

    speed = _DEFAULT_SERIAL_SPEED
    rtscts = False
    dsrdtr = False
    delay = 0.0
    if "," in spec:
        parts = spec.split(",")
        device = parts[0]
        for part in parts[1:]:
            if part == "rtscts":
                rtscts = True
            elif part == "dsrdtr":
                dsrdtr = True
            elif part == "delay":
                delay = _DEFAULT_SERIAL_DELAY
            elif part.isnumeric():
                speed = int(part)
            else:
                raise ValueError(f"Unknown serial moniker option: {part!r}")
    else:
        device = spec

    return SerialMoniker(
        device=device, speed=speed, rtscts=rtscts, dsrdtr=dsrdtr, delay=delay
    )


@contextlib.contextmanager
def serial_tcp_bridge(
    moniker: SerialMoniker,
    tcp_port: int,
) -> Generator[None, None, None]:
    """Start a TCP server on *tcp_port* that bridges to a serial port.

    Accepts one connection from the Android device (forwarded via ADB
    reverse-port) and bi-directionally relays data between the TCP
    client and the serial interface.
    """
    stop = threading.Event()
    active_conn: list[socket.socket] = []

    def relay_serial_to_tcp(
        ser: serial.Serial, conn: socket.socket, relay_stop: threading.Event
    ) -> None:
        try:
            while not relay_stop.is_set():
                data = ser.read(4096)
                if data:
                    conn.sendall(data)
        except Exception:
            pass
        finally:
            relay_stop.set()

    def relay_tcp_to_serial(
        conn: socket.socket, ser: serial.Serial, relay_stop: threading.Event
    ) -> None:
        try:
            while not relay_stop.is_set():
                try:
                    data = conn.recv(4096)
                except socket.timeout:
                    continue
                if not data:
                    break
                ser.write(data)
        except Exception:
            pass
        finally:
            relay_stop.set()

    def accept_and_bridge(server_sock: socket.socket) -> None:
        try:
            while not stop.is_set():
                try:
                    conn, addr = server_sock.accept()
                except socket.timeout:
                    continue
                except OSError:
                    return

                log(
                    f"Android device connected from {addr}, opening {moniker.device}@{moniker.speed}"
                )
                conn.settimeout(0.5)
                active_conn.append(conn)
                try:
                    ser = serial.Serial(
                        moniker.device,
                        baudrate=moniker.speed,
                        rtscts=moniker.rtscts,
                        dsrdtr=moniker.dsrdtr,
                        timeout=0.1,
                    )
                except Exception as exc:
                    log(f"Failed to open serial port {moniker.device}: {exc}")
                    active_conn.remove(conn)
                    with contextlib.suppress(OSError):
                        conn.close()
                    stop.set()
                    return

                if moniker.delay > 0.0:
                    log(f"Waiting {moniker.delay}s after opening serial port")
                    time.sleep(moniker.delay)

                relay_stop = threading.Event()
                t1 = threading.Thread(
                    target=relay_serial_to_tcp,
                    args=(ser, conn, relay_stop),
                    name="serial->tcp",
                )
                t2 = threading.Thread(
                    target=relay_tcp_to_serial,
                    args=(conn, ser, relay_stop),
                    name="tcp->serial",
                )
                t1.start()
                t2.start()
                t1.join()
                t2.join()
                active_conn.remove(conn)
                with contextlib.suppress(OSError):
                    conn.close()
                with contextlib.suppress(Exception):
                    ser.close()
        except Exception as exc:
            log(f"Bridge error: {exc}")
            stop.set()

    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind(("127.0.0.1", tcp_port))
    server_sock.listen(1)
    server_sock.settimeout(1.0)
    log(
        f"Serial-TCP bridge listening on 127.0.0.1:{tcp_port}"
        f" -> {moniker.device}@{moniker.speed}"
        + (" [rtscts]" if moniker.rtscts else "")
        + (" [dsrdtr]" if moniker.dsrdtr else "")
    )

    accept_thread = threading.Thread(
        target=accept_and_bridge,
        args=(server_sock,),
        name="bridge-accept",
    )
    accept_thread.start()

    try:
        yield
    finally:
        stop.set()
        for c in list(active_conn):
            with contextlib.suppress(OSError):
                c.shutdown(socket.SHUT_RDWR)
        with contextlib.suppress(OSError):
            server_sock.close()
        accept_thread.join()


# ---------------------------------------------------------------------------
# Test runner
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--bleak-hci-transport",
        action="store",
        default=None,
        help=(
            "Bumble serial transport moniker "
            "(e.g. 'serial:/dev/ttyUSB0,1000000'). "
            "See https://google.github.io/bumble/transports/serial.html"
        ),
    )
    args = parser.parse_args()

    moniker = (
        parse_serial_moniker(args.bleak_hci_transport)
        if args.bleak_hci_transport is not None
        else None
    )

    if moniker is not None:
        log(f"Checking serial port {moniker.device} ...")
        try:
            ser = serial.Serial(moniker.device, baudrate=moniker.speed, timeout=0.1)
            ser.close()
        except serial.SerialException as exc:
            log(f"Failed to open serial port {moniker.device}: {exc}")
            sys.exit(1)

    # Resolve ADB early so we fail fast if it is missing
    adb = ADB()
    log(f"Using adb: {adb.adb_executable}")

    briefcase_dir = Path(__file__).parent
    log(f"Starting Android tests (briefcase run) in {briefcase_dir}")

    briefcase_extra_args: list[str] = []
    if moniker is not None:
        briefcase_extra_args += [
            f"--reverse-port={DEVICE_PORT}",
            "--",
            f"--bleak-hci-transport=tcp-client:127.0.0.1:{DEVICE_PORT}",
        ]

    ctx = (
        serial_tcp_bridge(moniker, DEVICE_PORT)
        if moniker is not None
        else contextlib.nullcontext()
    )
    with ctx:
        subprocess.run(
            [
                "briefcase",
                "run",
                "Android",
                "Gradle",
                "--test",
                "--update",
                "--update-requirements",
                *briefcase_extra_args,
                # "--log-cli-level=DEBUG",  # uncomment for verbose pytest output
            ],
            cwd=briefcase_dir,
            stdout=sys.stdout,
            stderr=sys.stderr,
            check=True,
        )

    # log("Pulling coverage results from device")
    # adb.call_adb(
    #     [
    #         "pull",
    #         "/storage/emulated/0/Android/data/com.bleak.testbed.bleak_testbed/files/htmlcov",
    #         ".",
    #     ]
    # )

    log("Done.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Run Android integration tests."""

import argparse
import contextlib
import os
import shutil
import subprocess
import sys
import threading
import time
from collections.abc import Generator
from pathlib import Path

import uiautomator2 as u2  # pyright: ignore[reportMissingTypeStubs]
from bumble.transport.android_netsim import find_grpc_port

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
# Background worker threads
# ---------------------------------------------------------------------------

NETSIM_DEVICE_PORT = 8000
AVD_NAME = "beePhone"


def _find_emulator_serial(adb: ADB, avd_name: str) -> str | None:
    """Return the ADB serial for the running AVD with the given name, or None."""
    try:
        output = adb.call_adb(["devices"])
        for line in output.splitlines():
            parts = line.split()
            if (
                len(parts) >= 2
                and parts[1] == "device"
                and parts[0].startswith("emulator-")
            ):
                serial = parts[0]
                try:
                    name_output = adb.call_adb(["-s", serial, "emu", "avd", "name"])
                    if name_output.splitlines()[0].strip() == avd_name:
                        return serial
                except Exception:
                    pass
    except Exception:
        pass
    return None


def _wait_for_emulator_boot(
    adb: ADB, avd_name: str, stop_event: threading.Event
) -> str | None:
    """Poll until the named AVD has fully booted. Returns its serial, or None if stopped."""
    log(f"Waiting for AVD '{avd_name}' to boot...")
    while not stop_event.is_set():
        serial = _find_emulator_serial(adb, avd_name)
        if serial is not None:
            try:
                boot_prop = adb.call_adb(
                    ["-s", serial, "shell", "getprop", "sys.boot_completed"]
                )
                if boot_prop.strip() == "1":
                    log(f"Emulator '{avd_name}' ({serial}) is fully booted.")
                    return serial
            except Exception:
                pass
        stop_event.wait(2.0)
    return None


def _accept_permissions(d: u2.Device) -> None:
    ALLOW_PERMISSION_IDENTIFIERS = [
        "com.android.permissioncontroller:id/permission_allow_button",
        "com.android.packageinstaller:id/permission_allow_button",
    ]
    for rid in ALLOW_PERMISSION_IDENTIFIERS:
        btn = d(resourceId=rid)
        if btn.exists:
            log(f"Clicking allow permission button {rid}...")
            btn.click()  # pyright: ignore[reportUnknownMemberType]


def _accept_pairing(d: u2.Device) -> None:
    if not d(descriptionContains="Pairing request").exists:
        return

    log("Pairing request detected, opening notification bar...")
    d.open_notification()

    time.sleep(2)

    button = d(text="PAIR & CONNECT")
    if button.exists:
        time.sleep(0.5)
        log("Clicking pairing notification button...")
        button.click()  # pyright: ignore[reportUnknownMemberType]

    log("Closing notification bar...")
    d.press("back")  # pyright: ignore[reportUnknownMemberType]

    # Wait for the "Pair with Bleak?" confirmation popup
    deadline = time.time() + 3.0
    while time.time() < deadline:
        pair_btn = d(text="PAIR")
        if pair_btn.exists:
            time.sleep(0.5)
            log("Clicking PAIR button...")
            pair_btn.click()  # pyright: ignore[reportUnknownMemberType]
            break
        time.sleep(0.25)

    # wait a little, so that all menus/popups are fully closed
    time.sleep(2)


@contextlib.contextmanager
def _netsim_forwarding(
    adb: ADB, serial: str, stop_event: threading.Event
) -> Generator[int | None, None, None]:
    """Poll for the NetSim gRPC port, forward it to the device, and remove the rule on exit."""
    log("Polling for Android NetSim gRPC server...")
    forwarded_port: int | None = None
    while not stop_event.is_set():
        try:
            port = find_grpc_port(instance_number=0)
            if port != 0:
                log(
                    f"Found NetSim gRPC on port {port}, setting up ADB reverse forwarding "
                    f"(device:{NETSIM_DEVICE_PORT} -> host:{port})..."
                )
                adb.call_adb(
                    [
                        "-s",
                        serial,
                        "reverse",
                        f"tcp:{NETSIM_DEVICE_PORT}",
                        f"tcp:{port}",
                    ]
                )
                forwarded_port = port
                break
        except Exception as e:
            log(f"Error finding NetSim port: {e}")
        stop_event.wait(0.2)
    try:
        yield forwarded_port
    finally:
        if forwarded_port is not None:
            log(
                f"Removing ADB reverse forwarding for device port {NETSIM_DEVICE_PORT}..."
            )
            try:
                adb.call_adb(
                    ["-s", serial, "reverse", "--remove", f"tcp:{NETSIM_DEVICE_PORT}"]
                )
            except Exception as e:
                log(f"Failed to remove ADB reverse forwarding: {e}")


def _background_worker(adb: ADB, stop_event: threading.Event) -> None:
    """Wait for the emulator to boot, forward netsim, then accept permissions and pairings."""
    device_serial = _wait_for_emulator_boot(adb, AVD_NAME, stop_event)
    if device_serial is None:
        return  # stop_event was set before boot

    with _netsim_forwarding(adb, device_serial, stop_event) as forwarded_port:
        if forwarded_port is None:
            return  # stop_event was set before gRPC port was found

        d = u2.connect()
        while not stop_event.is_set():
            try:
                _accept_permissions(d)
            except Exception as e:
                log(f"Error in permission accept: {e}")
            try:
                _accept_pairing(d)
            except Exception as e:
                log(f"Error in pairing accept: {e}")
            stop_event.wait(0.25)


# ---------------------------------------------------------------------------
# Test runner
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--ci",
        action="store_true",
        help="Run in CI mode (headless emulator, shutdown on exit)",
    )
    args = parser.parse_args()

    # Resolve ADB early so we fail fast if it is missing
    adb = ADB()
    log(f"Using adb: {adb.adb_executable}")

    stop_event = threading.Event()
    worker = threading.Thread(
        target=_background_worker,
        args=(adb, stop_event),
        name="android-background-worker",
    )
    worker.start()

    try:
        briefcase_dir = Path(__file__).parent
        log(f"Starting Android emulator (briefcase run) in {briefcase_dir}")
        subprocess.run(
            [
                "briefcase",
                "run",
                "Android",
                "Gradle",
                "--test",
                "--update",
                "--update-requirements",
                "--device",
                f'{{"avd":"{AVD_NAME}", "device_type": "pixel"}}',
                *(
                    [
                        "--Xemulator=-no-window",
                        "--Xemulator=-no-snapshot",
                        "--Xemulator=-no-audio",
                        "--Xemulator=-no-boot-anim",
                    ]
                    if args.ci
                    else [
                        # Starting from a snapshot causes a "D/BluetoothAdapter: onBluetoothServiceDown" message in the first integration test.
                        # So we disable snapshots to ensure a clean start.
                        "--Xemulator=-no-snapshot",
                    ]
                ),
                "--revoke-permission=android.permission.BLUETOOTH_SCAN",
                "--revoke-permission=android.permission.BLUETOOTH_CONNECT",
                "--",
                f"--bleak-hci-transport=android-netsim:localhost:{NETSIM_DEVICE_PORT}",
                # "--log-cli-level=DEBUG",  # uncomment for verbose pytest output
            ],
            cwd=briefcase_dir,
            stdout=sys.stdout,
            stderr=sys.stderr,
            check=True,
        )
    finally:
        stop_event.set()
        worker.join()

    DEVICE_FILES_DIR = (
        "/storage/emulated/0/Android/data/com.bleak.testbed.bleak_testbed/files"
    )
    log("Pulling coverage results from device")
    for artifact in ["htmlcov", "coverage.xml", "junit.xml"]:
        adb.call_adb(["pull", f"{DEVICE_FILES_DIR}/{artifact}", "."])

    if args.ci:
        # Stop the emulator if we started in CI mode, so that it is started fresh on the next run.
        log("Stopping emulator...")
        adb.call_adb(
            [
                "emu",
                "kill",
            ]
        )

    log("Done.")


if __name__ == "__main__":
    main()

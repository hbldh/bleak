"""A private dbus-daemon with a fake BlueZ service for the BlueZ backend tests.

This module imports dbus_fast, so only import it on Linux.
"""

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    if sys.platform != "linux":
        assert False, "This backend is only available on Linux"

import asyncio
import contextlib
import tempfile
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Annotated

import pytest
from dbus_fast import DBusError
from dbus_fast.aio.message_bus import MessageBus
from dbus_fast.annotations import (
    DBusBool,
    DBusDict,
    DBusObjectPath,
    DBusSignature,
    DBusStr,
)
from dbus_fast.constants import BusType, PropertyAccess
from dbus_fast.service import ServiceInterface, dbus_property, method

from bleak._compat import timeout as async_timeout
from bleak.backends.bluezdbus import defs

from .conftest import ADAPTER_PATH, DEVICE_ADDRESS, DEVICE_PATH

DBusStrArray = Annotated[list[str], DBusSignature("as")]


class FakeAdapter1(ServiceInterface):
    """A stand-in for the BlueZ org.bluez.Adapter1 interface.

    Records the discovery method calls it receives in :attr:`calls`. Each
    discovery method answers from its list in :attr:`errors` in order, where
    ``None`` means success, and succeeds once the list is used up.
    """

    def __init__(self) -> None:
        super().__init__(defs.ADAPTER_INTERFACE)
        self.calls: list[str] = []
        self.errors: dict[str, list[str | None]] = {
            "SetDiscoveryFilter": [],
            "StartDiscovery": [],
            "StopDiscovery": [],
        }

    def _answer(self, member: str) -> None:
        self.calls.append(member)
        errors = self.errors[member]
        if errors and (error := errors.pop(0)) is not None:
            raise DBusError(error, f"fake {member} error")

    @dbus_property(access=PropertyAccess.READ)
    def Powered(self) -> DBusBool:
        return True

    @dbus_property(access=PropertyAccess.READ)
    def Roles(self) -> DBusStrArray:
        return ["central", "peripheral"]

    @method()
    def SetDiscoveryFilter(self, filter: DBusDict) -> None:
        self._answer("SetDiscoveryFilter")

    @method()
    def StartDiscovery(self) -> None:
        self._answer("StartDiscovery")

    @method()
    def StopDiscovery(self) -> None:
        self._answer("StopDiscovery")


class FakeDevice1(ServiceInterface):
    """A stand-in for the BlueZ org.bluez.Device1 interface."""

    def __init__(self) -> None:
        super().__init__(defs.DEVICE_INTERFACE)
        self.connected = True

    @dbus_property(access=PropertyAccess.READ)
    def Connected(self) -> DBusBool:
        return self.connected

    def disconnect(self) -> None:
        """Signals the device disconnecting over the wire."""
        self.connected = False
        self.emit_properties_changed({"Connected": False})

    @dbus_property(access=PropertyAccess.READ)
    def ServicesResolved(self) -> DBusBool:
        return True

    @dbus_property(access=PropertyAccess.READ)
    def Adapter(self) -> DBusObjectPath:
        return ADAPTER_PATH

    @dbus_property(access=PropertyAccess.READ)
    def Address(self) -> DBusStr:
        return DEVICE_ADDRESS


# A minimal bus configuration so the test does not depend on the
# system's session bus setup (e.g. launchd on macOS).
BUS_CONFIG = f"""\
<!DOCTYPE busconfig PUBLIC "-//freedesktop//DTD D-Bus Bus Configuration 1.0//EN"
 "http://www.freedesktop.org/standards/dbus/1.0/busconfig.dtd">
<busconfig>
  <type>session</type>
  <listen>unix:tmpdir={tempfile.gettempdir()}</listen>
  <auth>EXTERNAL</auth>
  <policy context="default">
    <allow send_destination="*" eavesdrop="true"/>
    <allow eavesdrop="true"/>
    <allow own="*"/>
  </policy>
</busconfig>
"""


class RealDBusDaemon:
    """A private dbus-daemon standing in for the system bus.

    A fake org.bluez exporting an adapter and a connected device is
    served on the daemon by a second bus connection; dbus_fast answers
    GetManagedObjects for the exported objects itself.
    """

    def __init__(self) -> None:
        self.process: asyncio.subprocess.Process | None = None
        self.bluez_bus: MessageBus | None = None
        self.adapter = FakeAdapter1()
        self.device = FakeDevice1()

    async def start(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        config_file = tmp_path / "bus.conf"
        config_file.write_text(BUS_CONFIG)
        self.process = await asyncio.create_subprocess_exec(
            "dbus-daemon",
            f"--config-file={config_file}",
            "--nofork",
            "--print-address=1",
            stdout=asyncio.subprocess.PIPE,
        )
        try:
            assert self.process.stdout is not None
            async with async_timeout(10):
                address = (await self.process.stdout.readline()).decode().strip()
            assert address

            # BlueZManager hardcodes BusType.SYSTEM, so the address
            # environment variable is the only seam that redirects it to
            # the private daemon without patching internals
            monkeypatch.setenv("DBUS_SYSTEM_BUS_ADDRESS", address)

            self.bluez_bus = MessageBus(bus_type=BusType.SYSTEM)
            await self.bluez_bus.connect()
            self.bluez_bus.export(ADAPTER_PATH, self.adapter)
            self.bluez_bus.export(DEVICE_PATH, self.device)
            await self.bluez_bus.request_name(defs.BLUEZ_SERVICE)
        except BaseException:
            await self.stop()
            raise

    def kill(self) -> None:
        """Kill the daemon, causing a real socket death for all clients."""
        if self.bluez_bus is not None:
            with contextlib.suppress(Exception):
                self.bluez_bus.disconnect()
            self.bluez_bus = None
        if self.process is not None and self.process.returncode is None:
            self.process.kill()

    async def stop(self) -> None:
        """Kill the daemon and reap it."""
        self.kill()
        if self.process is not None:
            await self.process.wait()
            self.process = None


StartDaemon = Callable[[], Awaitable[RealDBusDaemon]]

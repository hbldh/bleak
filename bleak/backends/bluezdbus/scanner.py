import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    if sys.platform != "linux":
        assert False, "This backend is only available on Linux"

import logging
from collections.abc import Callable, Coroutine
from typing import Any, Literal, Optional
from warnings import warn

if sys.version_info < (3, 12):
    from typing_extensions import override
else:
    from typing import override

from dbus_fast import Variant

from bleak.args.bluez import BlueZDiscoveryFilters as _BlueZDiscoveryFilters
from bleak.args.bluez import BlueZScannerArgs as _BlueZScannerArgs
from bleak.backends.bluezdbus.defs import Device1
from bleak.backends.bluezdbus.manager import get_global_bluez_manager
from bleak.backends.scanner import (
    AdvertisementData,
    AdvertisementDataCallback,
    BaseBleakScanner,
)
from bleak.exc import BleakError

logger = logging.getLogger(__name__)


_DEPRECATED: dict[str, Any] = {
    "BlueZDiscoveryFilters": _BlueZDiscoveryFilters,
    "BlueZScannerArgs": _BlueZScannerArgs,
}


def __getattr__(name: str):
    if value := _DEPRECATED.get(name):
        warn(
            f"importing {name} from bleak.backends.bluezdbus.scanner is deprecated, use bleak.args.bluez instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


class BleakScannerBlueZDBus(BaseBleakScanner):
    """The native Linux Bleak BLE Scanner.

    For possible values for `filters`, see the parameters to the
    ``SetDiscoveryFilter`` method in the `BlueZ docs
    <https://github.com/bluez/bluez/blob/master/doc/org.bluez.Adapter.rst#void-setdiscoveryfilterdict-filter>`_

    Args:
        detection_callback:
            Optional function that will be called each time a device is
            discovered or advertising data has changed.
        service_uuids:
            Optional list of service UUIDs to filter on. Only advertisements
            containing this advertising data will be received. Specifying this
            also enables scanning while the screen is off on Android.
        scanning_mode:
            Set to ``"passive"`` to avoid the ``"active"`` scanning mode.
        **bluez:
            Dictionary of arguments specific to the BlueZ backend.
        **adapter (str):
            Bluetooth adapter to use for discovery.
    """

    def __init__(
        self,
        detection_callback: Optional[AdvertisementDataCallback],
        service_uuids: Optional[list[str]],
        scanning_mode: Literal["active", "passive"],
        *,
        bluez: _BlueZScannerArgs,
        **kwargs: Any,
    ):
        super(BleakScannerBlueZDBus, self).__init__(detection_callback, service_uuids)

        self._scanning_mode = scanning_mode

        # kwarg "device" is for backwards compatibility
        self._adapter: Optional[str] = kwargs.get("adapter", kwargs.get("device"))

        # callback from manager for stopping scanning if it has been started
        self._stop: Optional[Callable[[], Coroutine[Any, Any, None]]] = None

        # Discovery filters

        self._filters: dict[str, Variant] = {}

        self._filters["Transport"] = Variant("s", "le")
        self._filters["DuplicateData"] = Variant("b", False)

        if self._service_uuids:
            self._filters["UUIDs"] = Variant("as", self._service_uuids)

        filters = bluez.get("filters")

        if filters is not None:
            self.set_scanning_filter(filters=filters)

        self._or_patterns = bluez.get("or_patterns")

        if self._scanning_mode == "passive" and service_uuids:
            logger.warning(
                "service uuid filtering is not implemented for passive scanning, use bluez or_patterns as a workaround"
            )

        if self._scanning_mode == "passive" and not self._or_patterns:
            raise BleakError("passive scanning mode requires bluez or_patterns")

    @override
    async def start(self) -> None:
        manager = await get_global_bluez_manager()

        if self._adapter:
            adapter_path = f"/org/bluez/{self._adapter}"
        else:
            adapter_path = manager.get_default_adapter()

        self.seen_devices = {}

        if self._scanning_mode == "passive":
            self._stop = await manager.passive_scan(
                adapter_path,
                self._or_patterns,
                self._handle_advertising_data,
                self._handle_device_removed,
            )
        else:
            self._stop = await manager.active_scan(
                adapter_path,
                self._filters,
                self._handle_advertising_data,
                self._handle_device_removed,
            )

    @override
    async def stop(self) -> None:
        if self._stop:
            # avoid reentrancy
            stop, self._stop = self._stop, None

            await stop()

    def set_scanning_filter(self, **kwargs: Any) -> None:
        """Sets OS level scanning filters for the BleakScanner.

        For possible values for `filters`, see the parameters to the
        ``SetDiscoveryFilter`` method in the `BlueZ docs
        <https://github.com/bluez/bluez/blob/master/doc/org.bluez.Adapter.rst#void-setdiscoveryfilterdict-filter>`_

        See variant types here: <https://python-dbus-next.readthedocs.io/en/latest/type-system/>

        Keyword Args:
            filters (dict): A dict of filters to be applied on discovery.

        """
        for k, v in kwargs.get("filters", {}).items():
            if k == "UUIDs":
                self._filters[k] = Variant("as", v)
            elif k == "RSSI":
                self._filters[k] = Variant("n", v)
            elif k == "Pathloss":
                self._filters[k] = Variant("n", v)
            elif k == "Transport":
                self._filters[k] = Variant("s", v)
            elif k == "DuplicateData":
                self._filters[k] = Variant("b", v)
            elif k == "Discoverable":
                self._filters[k] = Variant("b", v)
            elif k == "Pattern":
                self._filters[k] = Variant("s", v)
            else:
                logger.warning("Filter '%s' is not currently supported." % k)

    # Helper methods

    def _handle_advertising_data(self, path: str, props: Device1) -> None:
        """
        Handles advertising data received from the BlueZ manager instance.

        Args:
            path: The D-Bus object path of the device.
            props: The D-Bus object properties of the device.
        """
        _service_uuids = props.get("UUIDs", [])

        if not self.is_allowed_uuid(_service_uuids):
            return

        # Get all the information wanted to pack in the advertisement data
        _local_name = props.get("Name")
        _manufacturer_data = {
            k: bytes(v) for k, v in props.get("ManufacturerData", {}).items()
        }
        _service_data = {k: bytes(v) for k, v in props.get("ServiceData", {}).items()}

        # Get tx power data
        tx_power = props.get("TxPower")

        # Pack the advertisement data
        advertisement_data = AdvertisementData(
            local_name=_local_name,
            manufacturer_data=_manufacturer_data,
            service_data=_service_data,
            service_uuids=_service_uuids,
            tx_power=tx_power,
            rssi=props.get("RSSI", -127),
            platform_data=(path, props),
        )

        device = self.create_or_update_device(
            path,
            props["Address"],
            # BlueZ generates a name based on the address if no name is available.
            # To match other backends, we replace this with None.
            (
                None
                if props["Alias"] == props["Address"].replace(":", "-")
                else props["Alias"]
            ),
            {"path": path, "props": props},
            advertisement_data,
        )

        self.call_detection_callbacks(device, advertisement_data)

    def _handle_device_removed(self, device_path: str) -> None:
        """
        Handles a device being removed from BlueZ.
        """
        try:
            del self.seen_devices[device_path]
        except KeyError:
            # The device will not have been added to self.seen_devices if no
            # advertising data was received, so this is expected to happen
            # occasionally.
            pass

import logging
from typing import Callable, Coroutine, Dict, List, Optional

from dbus_next import Variant
from typing_extensions import Literal

from ..device import BLEDevice
from ..scanner import AdvertisementData, AdvertisementDataCallback, BaseBleakScanner
from .manager import Device1, get_global_bluez_manager

logger = logging.getLogger(__name__)


class BleakScannerBlueZDBus(BaseBleakScanner):
    """The native Linux Bleak BLE Scanner.

    For possible values for `filters`, see the parameters to the
    ``SetDiscoveryFilter`` method in the `BlueZ docs
    <https://git.kernel.org/pub/scm/bluetooth/bluez.git/tree/doc/adapter-api.txt?h=5.48&id=0d1e3b9c5754022c779da129025d493a198d49cf>`_

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
        **adapter (str):
            Bluetooth adapter to use for discovery.
        **filters (dict):
            A dict of filters to be applied on discovery.
    """

    def __init__(
        self,
        detection_callback: Optional[AdvertisementDataCallback] = None,
        service_uuids: Optional[List[str]] = None,
        scanning_mode: Literal["active", "passive"] = "active",
        **kwargs,
    ):
        super(BleakScannerBlueZDBus, self).__init__(detection_callback, service_uuids)

        if scanning_mode == "passive":
            raise NotImplementedError

        # kwarg "device" is for backwards compatibility
        self._adapter = kwargs.get("adapter", kwargs.get("device", "hci0"))
        self._adapter_path: str = f"/org/bluez/{self._adapter}"

        # map of d-bus object path to d-bus object properties
        self._devices: Dict[str, Device1] = {}

        # callback from manager for stopping scanning if it has been started
        self._stop: Optional[Callable[[], Coroutine]] = None

        # Discovery filters

        self._filters: Dict[str, Variant] = {}

        self._filters["Transport"] = Variant("s", "le")
        self._filters["DuplicateData"] = Variant("b", False)

        if self._service_uuids:
            self._filters["UUIDs"] = Variant("as", self._service_uuids)

        self.set_scanning_filter(**kwargs)

    async def start(self):
        manager = await get_global_bluez_manager()

        self._devices.clear()

        self._stop = await manager.active_scan(
            self._adapter_path, self._filters, self._handle_advertising_data
        )

    async def stop(self):
        if self._stop:
            # avoid reentrancy
            stop, self._stop = self._stop, None

            await stop()

    def set_scanning_filter(self, **kwargs):
        """Sets OS level scanning filters for the BleakScanner.

        For possible values for `filters`, see the parameters to the
        ``SetDiscoveryFilter`` method in the `BlueZ docs
        <https://git.kernel.org/pub/scm/bluetooth/bluez.git/tree/doc/adapter-api.txt?h=5.48&id=0d1e3b9c5754022c779da129025d493a198d49cf>`_

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

    @property
    def discovered_devices(self) -> List[BLEDevice]:
        # Reduce output.
        discovered_devices = []
        for path, props in self._devices.items():
            if not props:
                logger.debug(
                    "Disregarding %s since no properties could be obtained." % path
                )
                continue

            uuids = props.get("UUIDs", [])
            manufacturer_data = props.get("ManufacturerData", {})
            discovered_devices.append(
                BLEDevice(
                    props["Address"],
                    props["Alias"],
                    {"path": path, "props": props},
                    props.get("RSSI", 0),
                    uuids=uuids,
                    manufacturer_data=manufacturer_data,
                )
            )
        return discovered_devices

    # Helper methods

    def _handle_advertising_data(self, path: str, props: Device1) -> None:
        """
        Handles advertising data received from the BlueZ manager instance.

        Args:
            path: The D-Bus object path of the device.
            props: The D-Bus object properties of the device.
        """

        self._devices[path] = props

        if self._callback is None:
            return

        # Get all the information wanted to pack in the advertisement data
        _local_name = props.get("Name")
        _manufacturer_data = {
            k: bytes(v) for k, v in props.get("ManufacturerData", {}).items()
        }
        _service_data = {k: bytes(v) for k, v in props.get("ServiceData", {}).items()}
        _service_uuids = props.get("UUIDs", [])

        # Pack the advertisement data
        advertisement_data = AdvertisementData(
            local_name=_local_name,
            manufacturer_data=_manufacturer_data,
            service_data=_service_data,
            service_uuids=_service_uuids,
            platform_data=props,
        )

        device = BLEDevice(
            props["Address"],
            props["Alias"],
            {"path": path, "props": props},
            props.get("RSSI", 0),
            uuids=_service_uuids,
            manufacturer_data=_manufacturer_data,
        )

        self._callback(device, advertisement_data)

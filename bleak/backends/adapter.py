from collections.abc import Iterable
from typing import Any

from bleak._compat import Self
from bleak.backends import BleakBackend, get_default_backend
from bleak.backends.device import BLEDevice
from bleak.exc import BleakError


class BaseBleakAdapter:
    """Interface for Bleak Bluetooth adapter operations.

    Provides operations that do not require active scanning, such as
    retrieving devices that are already connected to the system.

    Instances should be obtained via :meth:`get`.

    .. versionadded:: unreleased
    """

    @classmethod
    async def get(cls, **kwargs: Any) -> Self:
        """Get a Bluetooth adapter for the current platform.

        Returns:
            A platform-specific :class:`BaseBleakAdapter` instance.

        Raises:
            NotImplementedError: if the current backend does not support this.
        """
        raise NotImplementedError("get is not implemented for this backend")

    async def get_connected_devices(
        self, service_uuids: Iterable[str]
    ) -> list[BLEDevice]:
        """Retrieve BLE devices that are currently connected to the system.

        Args:
            service_uuids: Service UUIDs to filter on.

        Returns:
            A list of :class:`BLEDevice` for each connected BLE device.

        Raises:
            NotImplementedError: if the current backend does not support this.
        """
        raise NotImplementedError(
            "get_connected_devices is not implemented for this backend"
        )


def get_platform_adapter_backend_type() -> tuple[type[BaseBleakAdapter], BleakBackend]:
    """
    Gets the platform-specific :class:`BaseBleakAdapter` type.
    """
    backend = get_default_backend()
    match backend:
        case BleakBackend.BLUEZ_DBUS:
            from bleak.backends.bluezdbus.adapter import (
                BleakAdapterBlueZDBus,  # type: ignore
            )

            return (BleakAdapterBlueZDBus, backend)  # type: ignore

        case BleakBackend.CORE_BLUETOOTH:
            from bleak.backends.corebluetooth.adapter import (
                BleakAdapterCoreBluetooth,  # type: ignore
            )

            return (BleakAdapterCoreBluetooth, backend)  # type: ignore

        case BleakBackend.WIN_RT:
            from bleak.backends.winrt.adapter import BleakAdapterWinRT  # type: ignore

            return (BleakAdapterWinRT, backend)  # type: ignore

        case _:
            raise BleakError(f"Unsupported backend: {backend}")

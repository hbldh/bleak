from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    if sys.platform != "android":
        assert False, "This backend is only available on Android"

import asyncio
import logging
from typing import Callable

from android import Manifest
from android.content.pm import PackageManager
from android.os import Build
from java import jint
from java.chaquopy import JavaArray
from java.lang import String

from bleak.backends.android.utils import activity
from bleak.exc import (
    BleakBluetoothNotAvailableError,
    BleakBluetoothNotAvailableReason,
    BleakError,
)

logger = logging.getLogger(__name__)


def _has_permission(permission: str) -> bool:
    """Check if a permission is granted"""
    result = activity.checkSelfPermission(permission)
    return result == PackageManager.PERMISSION_GRANTED


def _request_permissions(
    permissions: list[str],
    callback: Callable[[JavaArray[String], JavaArray[jint]], None],
) -> None:
    """Request permissions from the user."""
    try:
        from toga.app import App as TogaCoreApp
        from toga_android.app import App as TogaAndroidApp
    except ImportError:  # pragma: no cover
        raise BleakError("Toga is not installed, cannot request permissions.")

    def _get_running_toga_android_app() -> TogaAndroidApp:
        """Get the currently running toga app"""
        app = TogaCoreApp.app
        if app is None:
            raise BleakError("No running toga app detected.")  # pragma: no cover
        impl = app._impl  # pyright: ignore[reportPrivateUsage]
        if not isinstance(impl, TogaAndroidApp):
            raise BleakError(f"'{app}' is an invalid app")  # pragma: no cover
        return impl

    android_app = _get_running_toga_android_app()
    android_app.request_permissions(
        permissions,
        on_complete=callback,
    )


def _required_ble_permissions() -> list[str]:
    """
    Get the required BLE permissions.

    This depends on the Android API Version.
    """
    api_level = Build.VERSION.SDK_INT
    if (
        api_level >= 23 and api_level <= 30
    ):  # pragma: no cover  # Can not be tested in CI, because netsim requires min. API 31
        return [
            Manifest.permission.ACCESS_FINE_LOCATION,
            Manifest.permission.ACCESS_BACKGROUND_LOCATION,  # optional: only if scanning BLE devices in background
        ]
    elif api_level > 30:
        return [
            Manifest.permission.BLUETOOTH_SCAN,
            Manifest.permission.BLUETOOTH_CONNECT,
        ]
    else:
        raise ValueError("unknown api level")  # pragma: no cover


async def check_for_permissions(loop: asyncio.AbstractEventLoop):
    required_ble_permissions = _required_ble_permissions()

    # Check if permissions are already granted
    permissions_granted = all(_has_permission(p) for p in required_ble_permissions)
    if permissions_granted:
        return

    permission_acknowledged = loop.create_future()

    def handle_permissions(
        permissions: JavaArray[String],
        grantResults: JavaArray[jint],
    ):
        logger.debug(f"Permissions result: {permissions=}, {grantResults=}")
        grant_results = [
            granted_result == PackageManager.PERMISSION_GRANTED
            for granted_result in grantResults
        ]
        if all(grant_results):
            loop.call_soon_threadsafe(
                permission_acknowledged.set_result,
                grant_results,
            )
        else:
            loop.call_soon_threadsafe(  # pragma: no cover  # Difficult to test user denial in CI. This would require a second run of the test suite with different user interaction.
                permission_acknowledged.set_exception,
                BleakBluetoothNotAvailableError(
                    f"User denied access to {permissions}",
                    BleakBluetoothNotAvailableReason.DENIED_BY_USER,
                ),
            )

    # Request the permissions
    _request_permissions(
        required_ble_permissions,
        handle_permissions,
    )
    await permission_acknowledged

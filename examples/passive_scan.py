"""
Scanner using passive scanning mode
--------------

Example similar to detection_callback.py, but using passive scanning

Updated on 2022-11-24 by bojanpotocnik <info@bojanpotocnik.com>

"""
import argparse
import asyncio
import logging
from typing import Optional, List, Dict, Any

import bleak
from bleak import AdvertisementData, BLEDevice, BleakScanner

logger = logging.getLogger(__name__)


def _get_os_specific_scanning_params(
    uuids: Optional[List[str]],
    rssi: Optional[int] = None,
    macos_use_bdaddr: bool = False,
) -> Dict[str, Any]:
    def get_bluez_dbus_scanning_params() -> Dict[str, Any]:
        from bleak.assigned_numbers import AdvertisementDataType
        from bleak.backends.bluezdbus.advertisement_monitor import OrPattern
        from bleak.backends.bluezdbus.scanner import (
            BlueZScannerArgs,
            BlueZDiscoveryFilters,
        )

        filters = BlueZDiscoveryFilters(
            # UUIDs= Added below, because it cannot be None
            # RSSI= Added below, because it cannot be None
            Transport="le",
            DuplicateData=True,
        )
        if uuids:
            filters["UUIDs"] = uuids
        if rssi:
            filters["RSSI"] = rssi

        # or_patterns ar required for BlueZ passive scanning
        or_patterns = [
            # General Discoverable (peripherals)
            OrPattern(0, AdvertisementDataType.FLAGS, b"\x02"),
            # BR/EDR Not Supported (BLE peripherals)
            OrPattern(0, AdvertisementDataType.FLAGS, b"\x04"),
            # General Discoverable, BR/EDR Not Supported (BLE peripherals)
            OrPattern(0, AdvertisementDataType.FLAGS, b"\x06"),
            # General Discoverable, LE and BR/EDR Capable (Controller), LE and BR/EDR Capable (Host) (computers, phones)
            OrPattern(0, AdvertisementDataType.FLAGS, b"\x1A"),
        ]

        return {"bluez": BlueZScannerArgs(filters=filters, or_patterns=or_patterns)}

    def get_core_bluetooth_scanning_params() -> Dict[str, Any]:
        from bleak.backends.corebluetooth.scanner import CBScannerArgs

        return {"cb": CBScannerArgs(use_bdaddr=macos_use_bdaddr)}

    return {
        "BleakScannerBlueZDBus": get_bluez_dbus_scanning_params,
        "BleakScannerCoreBluetooth": get_core_bluetooth_scanning_params,
        # "BleakScannerP4Android": get_p4android_scanning_params,
        # "BleakScannerWinRT": get_winrt_scanning_params,
    }.get(bleak.get_platform_scanner_backend_type().__name__, lambda: {})()


async def scan(args: argparse.Namespace, passive_mode: bool):
    def scan_callback(device: BLEDevice, adv_data: AdvertisementData):
        logger.info("%s: %r", device.address, adv_data)

    async with BleakScanner(
        detection_callback=scan_callback,
        **_get_os_specific_scanning_params(
            uuids=args.services, macos_use_bdaddr=args.macos_use_bdaddr
        ),
        scanning_mode="passive" if passive_mode else "active",
    ):
        await asyncio.sleep(60)


async def main(args: argparse.Namespace):
    try:
        await scan(args, passive_mode=True)
    except bleak.exc.BleakNoPassiveScanError as e:
        if args.fallback:
            logger.warning(
                f"Passive scanning not possible, using active scanning ({e})"
            )
            await scan(args, passive_mode=False)
        else:
            logger.error(f"Passive scanning not possible ({e})")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)-15s %(name)-8s %(levelname)s: %(message)s",
    )

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--fallback",
        action="store_true",
        help="fallback to active scanning mode if passive mode is not possible",
    )
    parser.add_argument(
        "--macos-use-bdaddr",
        action="store_true",
        help="when true use Bluetooth address instead of UUID on macOS",
    )
    parser.add_argument(
        "--services",
        metavar="<uuid>",
        nargs="*",
        help="UUIDs of one or more services to filter for",
    )

    arguments = parser.parse_args()

    try:
        asyncio.run(main(arguments))
    except KeyboardInterrupt:
        pass

import asyncio

from bumble.transport.common import Transport

from bleak import BleakScanner

# The Linux kernel stops an LE-only scan on its own after DISCOV_LE_TIMEOUT
# (10.24 s) and BlueZ re-arms it IDLE_DISCOV_TIMEOUT (5 s) later. A stop that
# lands in that gap is rejected by the kernel and surfaces as InProgress.
SCAN_DURATION = 12.0


async def test_stop_after_kernel_le_scan_timeout(hci_transport: Transport) -> None:
    """
    Regression test for <https://github.com/hbldh/bleak/issues/2021>.
    """
    async with BleakScanner():
        await asyncio.sleep(SCAN_DURATION)

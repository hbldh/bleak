import asyncio

import pytest
from bumble.transport.common import Transport

from bleak import BleakScanner

# The kernel stops an LE-only scan after DISCOV_LE_TIMEOUT (10.24 s) and BlueZ
# restarts it IDLE_DISCOV_TIMEOUT (5 s) later. A stop that arrives while the
# kernel is between states is rejected and surfaces as InProgress; the window
# is narrow, so the stop is placed at several points around the restart.
STOP_AFTER = [10.0, 12.0, 15.0, 15.2, 15.4, 16.0]


@pytest.mark.parametrize("stop_after", STOP_AFTER)
async def test_stop_around_kernel_le_scan_restart(
    stop_after: float, hci_transport: Transport
) -> None:
    """
    Regression test for <https://github.com/hbldh/bleak/issues/2021>.
    """
    async with BleakScanner():
        await asyncio.sleep(stop_after)

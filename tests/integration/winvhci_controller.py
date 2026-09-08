import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    if sys.platform != "win32":
        assert False, "This is only available on Windows"


import asyncio
import contextlib
import logging
from collections.abc import AsyncGenerator

from bumble.controller import Controller
from bumble.link import LocalLink
from bumble.transport.common import Transport
from winrt.windows.devices.bluetooth import BluetoothAdapter
from winvhci.bumble_compat import (
    WindowsCompatController,
    WindowsCompatLink,
    apply_dual_mode,
)
from winvhci.device import VhciStats
from winvhci.transport import open_winvhci_transport

# Windows connects as central using this as its public identity address. It is
# also how our adapter is told apart from real hardware, the way the BlueZ
# equivalent uses its manufacturer ID.
WINVHCI_CONTROLLER_ADDRESS = "F0:F1:F2:F3:F4:F5"

logger = logging.getLogger(__name__)


def _address_to_int(address: str) -> int:
    """Convert "AA:BB:CC:DD:EE:FF" to the integer WinRT reports."""
    return int(address.replace(":", ""), 16)


async def wait_for_adapter_to_go(address: str, timeout: float = 90.0) -> None:
    """Wait until no Bluetooth adapter reports our controller's address.

    Must run before creating a radio: get_default_async keeps returning the
    previous radio's adapter until Windows has finished removing it, and every
    transport here uses the same address, so there is otherwise no way to tell
    the old radio from the new one.

    Do not shorten the timeout on the strength of a short measurement. Removal
    has a long tail - Windows retrying a radio it believes is out of range -
    that only full suite runs reach, measured at a repeatable 34s.
    """
    wanted = _address_to_int(address)
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout

    while loop.time() < deadline:
        adapter = await BluetoothAdapter.get_default_async()
        if (
            adapter is None  # pyright: ignore[reportUnnecessaryComparison]
            or adapter.bluetooth_address != wanted
        ):
            return
        # A cached entry for a radio that is already gone counts as gone.
        if not await _adapter_is_live(adapter):
            return
        await asyncio.sleep(0.25)

    raise TimeoutError(
        f"a Bluetooth adapter at {address} was still present after "
        f"{timeout:.0f}s. That is the radio from the previous test, whose "
        f"handle is closed but whose devnode Windows has not finished "
        f"removing. Well past the observed tail, so treat it as stuck rather "
        f"than slow."
    )


async def _adapter_is_live(adapter: BluetoothAdapter) -> bool:
    """Whether an adapter actually backs a radio that still exists.

    get_default_async can return a cached adapter for a radio Windows has
    already removed, and nothing about the object gives that away. Using it
    does: get_radio_async raises ERROR_NOT_FOUND.
    """
    try:
        radio = await adapter.get_radio_async()
    except OSError as error:
        logger.debug("adapter %s is stale: %s", adapter.device_id, error)
        return False
    return radio is not None  # pyright: ignore[reportUnnecessaryComparison]


async def wait_for_adapter(address: str, timeout: float = 30.0) -> BluetoothAdapter:
    """
    Wait for Windows to bring up a Bluetooth adapter for our radio.

    The counterpart of the BlueZ path's InterfacesAdded wait. It polls because
    BluetoothAdapter has no "adapter added" event, and it matches on address
    alone, which is sound only because wait_for_adapter_to_go runs first - so
    do not reorder or skip that call.

    There is deliberately no power-on step: Windows brings the radio up itself
    as BthPort initializes.
    """
    wanted = _address_to_int(address)
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    last_seen: int | None = None

    while loop.time() < deadline:
        adapter = await BluetoothAdapter.get_default_async()

        # The projection types this as non-optional, but a machine with no
        # Bluetooth at all is exactly what has to fail cleanly here.
        if adapter is None:  # pyright: ignore[reportUnnecessaryComparison]
            await asyncio.sleep(0.25)
            continue

        if adapter.bluetooth_address == wanted:
            if await _adapter_is_live(adapter):
                logger.info("adapter %s is up as %s", address, adapter.device_id)
                return adapter
            await asyncio.sleep(0.25)
            continue

        # A real radio on a developer machine. Recorded so the error below can
        # say so, rather than every test failing against the wrong adapter.
        last_seen = adapter.bluetooth_address
        await asyncio.sleep(0.25)

    if last_seen is not None:
        raise RuntimeError(
            f"the default Bluetooth adapter is "
            f"{last_seen:012X}, not the virtual controller's {wanted:012X}. "
            f"Another Bluetooth adapter is present and Windows prefers it."
        )
    raise RuntimeError(
        f"no new Bluetooth adapter appeared within {timeout}s. The winvhci "
        f"driver may not be installed, or Windows did not finish bringing the "
        f"radio up - see https://github.com/dlech/windows-vhci-driver"
    )


def read_stats(hci_transport: Transport) -> "VhciStats | None":
    """The driver's packet counters, or None if they cannot be read.

    Defensive because the client and the driver are versioned separately - the
    client comes from the pinned git tag, the driver from an installed release -
    so the client having stats() does not mean the driver implements the IOCTL.
    """
    device = getattr(hci_transport, "device", None)
    stats = getattr(device, "stats", None)
    if stats is None:
        logger.info("winvhci client has no stats support")
        return None
    try:
        return stats()
    except Exception:
        logger.warning(
            "could not read winvhci stats. The installed driver is probably "
            "older than the winvhci client.",
            exc_info=True,
        )
        return None


def check_for_packet_loss(
    hci_transport: Transport, baseline: "VhciStats | None"
) -> None:
    """
    Fail if the driver lost a packet while the tests were running.

    Loss is otherwise invisible: a dropped advertising report looks exactly
    like a device that was not advertising, so it surfaces as a flaky test
    somewhere else. Read before the transport closes, since the counters live
    behind the device handle.
    """
    s = read_stats(hci_transport)
    if s is None or baseline is None:
        return
    logger.info(
        "winvhci: %d packets to the stack, %d to the client, peak depths %d/%d/%d",
        s.writes_total,
        s.queued_to_user_total,
        s.host_to_ctrl_peak,
        s.pending_event_peak,
        s.pending_data_peak,
    )

    # Only allocation failures are a defect; the driver documents the split.
    # DropsNoClient counts packets produced after the handle closed, which is
    # what every teardown here does.
    lost = s.drops_alloc_failed - baseline.drops_alloc_failed
    vanished = s.drops_no_client - baseline.drops_no_client

    if vanished:
        logger.info(
            "winvhci discarded %d packet(s) with no client attached, which is "
            "the ordinary teardown race rather than loss during the tests",
            vanished,
        )

    if lost:
        raise AssertionError(
            f"the winvhci driver lost {lost} packet(s) to failed allocations. "
            f"Any discovery or notification failure in this run is suspect."
        )


@contextlib.asynccontextmanager
async def open_winvhci_bluetooth_controller_link() -> AsyncGenerator[LocalLink, None]:
    """
    Open a local link (virtual RF connection) to a bumble Bluetooth controller
    that is connected to the Windows Bluetooth stack through the winvhci driver.
    """
    await wait_for_adapter_to_go(WINVHCI_CONTROLLER_ADDRESS)

    # The radio's lifetime is this handle's lifetime, so the context manager is
    # what stops a failed test leaving a radio behind for the next one.
    async with await open_winvhci_transport() as hci_transport:
        # WindowsCompatLink rather than LocalLink: bumble's assumes an LE
        # packet's source is the sending controller's random address, which
        # does not hold for Windows connecting with its public address.
        link = WindowsCompatLink()

        # WindowsCompatController rather than Controller, for three reasons
        # recorded in winvhci.bumble_compat. Each shows up as the Windows stack
        # stopping mid-bring-up.
        windows_controller = WindowsCompatController(
            "BLEAK-TEST-WINVHCI",
            host_source=hci_transport.source,
            host_sink=hci_transport.sink,
            link=link,
            public_address=WINVHCI_CONTROLLER_ADDRESS,
        )

        # Bumble reports itself LE-only, and Windows stops dead after
        # Read_Local_Supported_Features when it sees that.
        apply_dual_mode(windows_controller)

        await wait_for_adapter(WINVHCI_CONTROLLER_ADDRESS)

        # After bring-up: the counters are cumulative for the life of the
        # device node, so each module would inherit earlier teardowns.
        baseline = read_stats(hci_transport)

        try:
            yield link
        finally:
            check_for_packet_loss(hci_transport, baseline)


@contextlib.asynccontextmanager
async def open_transport_with_winvhci() -> AsyncGenerator[Transport, None]:
    """
    Create a bumble HCI Transport connected to Windows via the winvhci driver
    and connect a Bluetooth controller for a peripheral device to it.
    """
    async with open_winvhci_bluetooth_controller_link() as local_link:
        peripheral_controller = Controller("BLEAK-TEST-PERIPHERAL", link=local_link)
        yield Transport(peripheral_controller, peripheral_controller)

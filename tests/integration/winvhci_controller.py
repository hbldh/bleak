import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    if sys.platform != "win32":
        assert False, "This is only available on Windows"


import asyncio
import contextlib
import logging
from collections.abc import AsyncGenerator
from typing import cast

from bumble.controller import Controller
from bumble.link import LocalLink
from bumble.transport.common import Transport
from winrt.windows.devices.bluetooth import BluetoothAdapter
from winvhci.bumble_compat import (
    WindowsCompatController,
    WindowsCompatLink,
    apply_dual_mode,
)
from winvhci.device import VhciDevice, VhciStats
from winvhci.transport import open_winvhci_transport

# Windows connects as central using this as its public identity address. It is
# also how our adapter is told apart from real hardware, the way the BlueZ
# equivalent uses its manufacturer ID.
WINVHCI_CONTROLLER_ADDRESS = "F0:F1:F2:F3:F4:F5"

logger = logging.getLogger(__name__)


def _address_to_int(address: str) -> int:
    """Convert "AA:BB:CC:DD:EE:FF" to the integer WinRT reports."""
    return int(address.replace(":", ""), 16)


async def wait_for_previous_radio_to_go(timeout: float = 90.0) -> None:
    """Wait until the driver reports no radio device node still alive.

    Must run before creating a radio. Closing the previous transport's handle
    removes its radio, but PnP takes seconds to tens of seconds to actually
    destroy the node - Windows retries a radio it believes has gone out of
    range before letting go - and opening the device again while it exists
    leaves Windows with two radios at one address.

    The driver counts live radio nodes itself, as ``radios_alive`` in its
    stats, and that counter exists for exactly this wait. Opening the device
    without sending the control packet creates no radio, so polling it here
    has no side effect. This replaced polling WinRT for the previous adapter
    to disappear, which had to see through get_default_async's cache of
    adapters whose radios were already gone.

    Do not shorten the timeout on the strength of a short measurement. The
    tail only shows up in full suite runs, measured at a repeatable 34s.
    """

    def radios_alive() -> int:
        with VhciDevice() as device:
            return device.stats().radios_alive

    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout

    while True:
        alive = await asyncio.to_thread(radios_alive)
        if alive == 0:
            return
        if loop.time() >= deadline:
            raise TimeoutError(
                f"the winvhci driver still reports {alive} radio node(s) alive "
                f"after {timeout:.0f}s. That is the radio from the previous "
                f"test, whose handle is closed but whose devnode Windows has "
                f"not finished removing. Well past the observed tail, so treat "
                f"it as stuck rather than slow."
            )
        await asyncio.sleep(0.25)


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
    alone, which is sound only because wait_for_previous_radio_to_go runs
    first - so do not reorder or skip that call.

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


def read_stats(hci_transport: Transport) -> VhciStats:
    """The driver's packet counters, read through the transport's handle.

    Not defensive: the client is pinned to the same release the workflow
    installs, so a missing IOCTL is a real mismatch and should fail the run,
    not turn the loss check below into a silent no-op.
    """
    # The transport re-exposes its VhciDevice as .device; Transport itself
    # has no such attribute, hence the cast.
    device = cast(VhciDevice, getattr(hci_transport, "device", None))
    return device.stats()


#: How long the driver's backlogs are given to drain before the teardown
#: check treats a non-zero depth as a stall. On a settled stack a read is
#: always pended, so depth is normally zero at every instant; the grace is for
#: a packet written a moment before the check.
BACKLOG_DRAIN_TIMEOUT = 2.0


async def check_for_packet_loss(hci_transport: Transport, baseline: VhciStats) -> None:
    """
    Fail if the driver lost, stalled or refused a packet during the tests.

    All three are otherwise invisible: a dropped advertising report looks
    exactly like a device that was not advertising, so it surfaces as a flaky
    test somewhere else. Read before the transport closes, since the counters
    live behind the device handle.

    - ``drops_alloc_failed`` is the one loss the driver can suffer. Only
      allocation failures are a defect; ``drops_no_client`` counts packets the
      stack produced after a handle closed, which every teardown here does.
    - ``pending_event_count`` and ``pending_data_count`` must drain to zero. A
      settled Windows stack keeps a read pended at all times, so a depth that
      stays non-zero is a packet parked on the backlog with the read it should
      have met parked behind it - the rendezvous stall fixed in winvhci 1.3.0.
    - ``writes_no_radio`` must not move. Once the radio is up every packet the
      peripheral sends must be admitted; a refusal means the stack stopped
      consuming under the test.
    """
    loop = asyncio.get_running_loop()
    deadline = loop.time() + BACKLOG_DRAIN_TIMEOUT
    while True:
        s = await asyncio.to_thread(read_stats, hci_transport)
        if (s.pending_event_count == 0 and s.pending_data_count == 0) or (
            loop.time() >= deadline
        ):
            break
        await asyncio.sleep(0.1)

    logger.info(
        "winvhci: %d packets to the stack, %d to the client, peak depths %d/%d/%d",
        s.writes_total,
        s.queued_to_user_total,
        s.host_to_ctrl_peak,
        s.pending_event_peak,
        s.pending_data_peak,
    )

    lost = s.drops_alloc_failed - baseline.drops_alloc_failed
    vanished = s.drops_no_client - baseline.drops_no_client
    refused = s.writes_no_radio - baseline.writes_no_radio

    if vanished:
        logger.info(
            "winvhci discarded %d packet(s) with no client attached, which is "
            "the ordinary teardown race rather than loss during the tests",
            vanished,
        )

    problems: list[str] = []
    if lost:
        problems.append(f"lost {lost} packet(s) to failed allocations")
    if s.pending_event_count or s.pending_data_count:
        problems.append(
            f"left {s.pending_event_count} event(s) and {s.pending_data_count} "
            f"ACL packet(s) undelivered on its backlogs for "
            f"{BACKLOG_DRAIN_TIMEOUT:.0f}s, which on a settled stack means a "
            f"read is parked behind them"
        )
    if refused:
        problems.append(
            f"refused {refused} write(s) because the radio was not started, "
            f"after it had already come up"
        )
    if problems:
        raise AssertionError(
            "the winvhci driver " + "; ".join(problems) + ". Any discovery or "
            "notification failure in this run is suspect."
        )


@contextlib.asynccontextmanager
async def open_winvhci_bluetooth_controller_link() -> AsyncGenerator[LocalLink, None]:
    """
    Open a local link (virtual RF connection) to a bumble Bluetooth controller
    that is connected to the Windows Bluetooth stack through the winvhci driver.
    """
    await wait_for_previous_radio_to_go()

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
        baseline = await asyncio.to_thread(read_stats, hci_transport)

        try:
            yield link
        finally:
            await check_for_packet_loss(hci_transport, baseline)


@contextlib.asynccontextmanager
async def open_transport_with_winvhci() -> AsyncGenerator[Transport, None]:
    """
    Create a bumble HCI Transport connected to Windows via the winvhci driver
    and connect a Bluetooth controller for a peripheral device to it.
    """
    async with open_winvhci_bluetooth_controller_link() as local_link:
        peripheral_controller = Controller("BLEAK-TEST-PERIPHERAL", link=local_link)
        yield Transport(peripheral_controller, peripheral_controller)

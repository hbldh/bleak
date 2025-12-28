import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    if sys.platform != "linux":
        assert False, "This is only available on Linux"


import asyncio
import contextlib
import logging
from typing import AsyncGenerator

from bumble.controller import Controller
from bumble.link import LocalLink
from bumble.transport import open_transport
from bumble.transport.common import Transport
from dbus_fast import BusType, Message, MessageType, Variant
from dbus_fast.aio.message_bus import MessageBus

from bleak._compat import timeout as async_timeout
from bleak.backends.bluezdbus import defs
from bleak.backends.bluezdbus.signals import MatchRules, add_match
from bleak.backends.bluezdbus.utils import assert_reply, get_dbus_authenticator

BLEAK_TEST_MANUFACTURER_ID = 0xB1EA

logger = logging.getLogger(__name__)


@contextlib.asynccontextmanager
async def open_message_bus() -> AsyncGenerator[MessageBus, None]:
    """
    Open a D-Bus message bus connection.
    """
    bus = MessageBus(bus_type=BusType.SYSTEM, auth=get_dbus_authenticator())
    try:
        await bus.connect()
        yield bus
    finally:
        bus.disconnect()
        await bus.wait_for_disconnect()


async def power_on_controller(
    bus: MessageBus, adapter_path: str, timeout: float = 2.0
) -> None:
    """
    Power on a Bluetooth controller via D-Bus.

    It may take some time for the adapter to fully configure itself after
    powering on. So we make multiple attempts until timeout is reached.
    """
    async with async_timeout(timeout):
        while True:
            try:
                reply = await bus.call(
                    Message(
                        destination=defs.BLUEZ_SERVICE,
                        path=adapter_path,
                        interface=defs.PROPERTIES_INTERFACE,
                        member="Set",
                        signature="ssv",
                        body=[defs.ADAPTER_INTERFACE, "Powered", Variant("b", True)],
                    )
                )
                assert_reply(reply)
                return
            except Exception as e:
                logger.debug("Failed to power on adapter at %s: %s", adapter_path, e)
                await asyncio.sleep(0.1)


@contextlib.asynccontextmanager
async def wait_for_new_adapter() -> (
    AsyncGenerator[tuple[MessageBus, asyncio.Future[str]], None]
):
    """
    Connect to D-Bus and wait for a new Bluetooth adapter to be added.

    Yields a Future that will be resolved with the adapter path when
    a new adapter is detected via InterfacesAdded signal.
    """
    async with open_message_bus() as bus:
        loop = asyncio.get_running_loop()
        adapter_path_future: asyncio.Future[str] = loop.create_future()

        def _on_interfaces_added(message: Message):
            if message.message_type != MessageType.SIGNAL:
                return
            if message.member != "InterfacesAdded":
                return

            obj_path, ifaces = message.body
            adapter = ifaces.get(defs.ADAPTER_INTERFACE)
            if not adapter:
                return

            # Check for our test manufacturer ID to identify the adapter
            if adapter["Manufacturer"].value != BLEAK_TEST_MANUFACTURER_ID:
                return

            if not adapter_path_future.done():
                adapter_path_future.set_result(obj_path)

        bus.add_message_handler(_on_interfaces_added)

        try:
            # Subscribe to InterfacesAdded signals
            reply = await add_match(
                bus,
                MatchRules(
                    interface=defs.OBJECT_MANAGER_INTERFACE,
                    member="InterfacesAdded",
                    arg0path="/org/bluez/",
                ),
            )
            assert_reply(reply)

            # Yield the future and bus for the caller to use
            yield bus, adapter_path_future
        finally:
            bus.remove_message_handler(_on_interfaces_added)


def _clear_bit(flags: bytes, bit_pos: int) -> bytes:
    int_flags = int.from_bytes(flags, byteorder="little")
    int_flags &= ~(1 << bit_pos)
    return int_flags.to_bytes(len(flags), byteorder="little")


@contextlib.asynccontextmanager
async def open_bluez_bluetooth_controller_link(
    hci_transport_name: str,
) -> AsyncGenerator[LocalLink, None]:
    """
    Open a local link (virtual RF connection) to a bumble Bluetooth
    controller that is connected to BlueZ.
    """
    async with wait_for_new_adapter() as (bus, adapter_path_future):
        # Open a HCI transport connected to the OS
        async with await open_transport(hci_transport_name) as hci_transport:
            # Local link to create virtual RF connection between multiple Bluetooth Controllers
            link = LocalLink()

            # Bluetooth controller that BlueZ can connect to.
            # (This will register itself to the link.)
            bluez_controller = Controller(
                "BLEAK-TEST-BLUEZ",
                host_source=hci_transport.source,
                host_sink=hci_transport.sink,
                link=link,
            )
            bluez_controller.manufacturer_name = BLEAK_TEST_MANUFACTURER_ID

            # HACK: Work around Bumble missing feature combined with Linux kernel
            # requirement. https://github.com/google/bumble/issues/841
            #
            # According to the Bluetooth spec:
            #
            #   C24: [HCI_LE_Enhanced_Connection_Complete event is] Mandatory if
            #   the LE Controller supports Connection State and either LE Feature (LL
            #   Privacy) or LE Feature (Extended Advertising) is supported, otherwise optional if
            #   the LE Controller supports Connection State, otherwise excluded.
            #
            # And the Linux kernel enforces this in hci_le_create_conn_sync().
            # It will get a timeout if one of these features is enabled and the
            # Enhanced Connection Complete event is not sent.
            #
            # However, Bumble (as of 0.0.220) always sends HCI_LE_Connection_Complete_Event
            # in response to HCI_LE_Create_Connection_Command even when it should
            # be sending HCI_LE_Enhanced_Connection_Complete_Event.
            #
            # For now, we can work around the issue by disabling LL Privacy and
            # Extended Advertising features in the BlueZ controller.
            #
            # Ideally, this should be fixed in Bumble.

            bluez_controller.le_features = _clear_bit(
                bluez_controller.le_features, 6  # LL Privacy
            )
            bluez_controller.le_features = _clear_bit(
                bluez_controller.le_features, 12  # Extended Advertising
            )

            # Wait up to 5 seconds for the new adapter to appear via InterfacesAdded
            adapter_path = await asyncio.wait_for(adapter_path_future, timeout=5.0)
            logging.info(f"New adapter detected at {adapter_path}")

            # Ensure controller is powered on. This also ensures that BlueZ has fully
            # initialized the adapter and it is ready for use.
            await power_on_controller(bus, adapter_path)

            # We dont need the bus anymore. We have done everything needed with it.
            # Bleak will open its own D-Bus connection.
            bus.disconnect()
            await bus.wait_for_disconnect()

            # Yield the local link for use in tests
            yield link


@contextlib.asynccontextmanager
async def open_transport_with_bluez_vhci() -> AsyncGenerator[Transport, None]:
    """
    Create a bumble HCI Transport connected to BlueZ via the vhci driver and connect
    a Bluetooth controller for a peripheral device to it.
    """
    async with open_bluez_bluetooth_controller_link("vhci") as local_link:
        peripheral_controller = Controller("BLEAK-TEST-PERIPHERAL", link=local_link)
        yield Transport(peripheral_controller, peripheral_controller)

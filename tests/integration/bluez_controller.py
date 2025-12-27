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

from bleak.backends.bluezdbus import defs
from bleak.backends.bluezdbus.signals import MatchRules, add_match
from bleak.backends.bluezdbus.utils import assert_reply, get_dbus_authenticator

if sys.version_info < (3, 11):
    from async_timeout import timeout as async_timeout
else:
    from asyncio import timeout as async_timeout


@contextlib.asynccontextmanager
async def open_message_bus() -> AsyncGenerator[MessageBus, None]:
    bus = MessageBus(bus_type=BusType.SYSTEM, auth=get_dbus_authenticator())
    await bus.connect()
    try:
        yield bus
    finally:
        if bus.connected:
            bus.disconnect()


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
                logging.warning(f"Failed to power on adapter at {adapter_path}: {e}")
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

            # New adapter found, return its path via the future
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
            Controller(
                "BLEAK-TEST-BLUEZ",
                host_source=hci_transport.source,
                host_sink=hci_transport.sink,
                link=link,
            )

            # Wait up to 5 seconds for the new adapter to appear via InterfacesAdded
            adapter_path = await asyncio.wait_for(adapter_path_future, timeout=5.0)
            logging.info(f"New adapter detected at {adapter_path}")

            # Ensure controller is powered on
            await power_on_controller(bus, adapter_path)

            # Disconnect from D-Bus
            bus.disconnect()

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

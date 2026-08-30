#!/usr/bin/env python

"""Tests for `bleak.backends.bluezdbus.client` package."""

import sys

import pytest

if sys.platform != "linux":
    pytest.skip("skipping linux-only tests", allow_module_level=True)
    assert False  # HACK: work around pyright bug

from unittest.mock import AsyncMock, Mock

from dbus_fast.aio import MessageBus
from dbus_fast.constants import MessageType
from dbus_fast.message import Message

from bleak.backends.bluezdbus.client import BleakClientBlueZDBus
from bleak.backends.service import BleakGATTServiceCollection

DEVICE_PATH = "/org/bluez/hci0/dev_11_22_33_44_55_66"


def make_connected_client() -> tuple[BleakClientBlueZDBus, Mock]:
    """
    Make a client that appears to be connected and give it a mocked D-Bus bus.

    Returns the client and the mocked bus so that tests can make assertions
    about how the bus was used.
    """
    bus = Mock(spec=MessageBus, connected=True)
    bus.wait_for_disconnect = AsyncMock()
    client = BleakClientBlueZDBus("11:22:33:44:55:66", timeout=10.0, bluez={})
    client._bus = bus  # pyright: ignore[reportPrivateUsage]
    client._device_path = DEVICE_PATH  # pyright: ignore[reportPrivateUsage]
    client._is_connected = True  # pyright: ignore[reportPrivateUsage]
    client.services = BleakGATTServiceCollection()
    return client, bus


def method_return() -> Message:
    """Makes a valid reply to a "Disconnect" method call."""
    return Message(
        message_type=MessageType.METHOD_RETURN,
        serial=2,
        reply_serial=1,
    )


def simulate_disconnected_signal(
    client: BleakClientBlueZDBus, bus: Mock, close_bus: bool = False
) -> None:
    """
    Simulate receiving the BlueZ "Disconnected" signal.

    This does what the ``on_connected_changed()`` callback does, plus it can
    also close the client's own D-Bus connection, which is what happens when
    the signal races a pending method call on that connection.
    """
    client._is_connected = False  # pyright: ignore[reportPrivateUsage]
    client.services = None  # pyright: ignore[reportPrivateUsage]
    if client._disconnecting_event is not None:  # pyright: ignore[reportPrivateUsage]
        client._disconnecting_event.set()  # pyright: ignore[reportPrivateUsage]
    if close_bus:
        # like the D-Bus connection being closed while a method call is
        # still pending, dbus-fast then raises EOFError for that call
        bus.connected = False


async def test_disconnect_not_connected():
    """Disconnecting a client that was never connected is a no-op."""
    client, bus = make_connected_client()
    client._bus = None  # pyright: ignore[reportPrivateUsage]

    await client.disconnect()

    bus.call.assert_not_called()
    bus.disconnect.assert_not_called()


async def test_disconnect():
    """Disconnecting a connected client closes the client D-Bus connection."""
    client, bus = make_connected_client()

    # the "Disconnected" signal arrives after the reply to the "Disconnect"
    # method call
    orig_call = AsyncMock(return_value=method_return())

    async def call_side_effect(msg: Message) -> Message:
        reply = await orig_call(msg)
        simulate_disconnected_signal(client, bus, close_bus=False)
        return reply

    bus.call = AsyncMock(side_effect=call_side_effect)

    await client.disconnect()

    bus.disconnect.assert_called_once()
    bus.wait_for_disconnect.assert_awaited_once()
    assert client.is_connected is False
    assert client._bus is None  # pyright: ignore[reportPrivateUsage]


async def test_disconnect_already_disconnected():
    """
    Disconnecting a client whose device was already disconnected by the
    peer only closes the client D-Bus connection.
    """
    client, bus = make_connected_client()
    simulate_disconnected_signal(client, bus, close_bus=False)

    await client.disconnect()

    bus.call.assert_not_called()
    bus.disconnect.assert_called_once()
    bus.wait_for_disconnect.assert_awaited_once()


async def test_disconnect_eoferror_when_bus_disconnected():
    """
    An ``EOFError`` from the "Disconnect" method call is treated as success
    if the client D-Bus connection was already closed.

    BlueZ's "Disconnected" signal arrives on the shared manager D-Bus
    connection and can race the reply to the client's own "Disconnect"
    method call. If the signal wins, the client's D-Bus connection is
    closed while the call is still pending, so dbus-fast fails the call
    with ``EOFError`` instead of a method reply, even though the device
    is disconnected.
    """
    client, bus = make_connected_client()

    async def call_side_effect(msg: Message) -> Message:
        assert msg.member == "Disconnect"
        # the "Disconnected" signal arrives before the reply to this
        # pending method call and the connection is closed
        simulate_disconnected_signal(client, bus, close_bus=True)
        raise EOFError

    bus.call = AsyncMock(side_effect=call_side_effect)

    await client.disconnect()

    # the bus was already closed, so it must not be closed a second time
    bus.disconnect.assert_not_called()
    bus.wait_for_disconnect.assert_not_awaited()
    assert client.is_connected is False
    assert client._bus is None  # pyright: ignore[reportPrivateUsage]


async def test_disconnect_eoferror_when_bus_connected():
    """An ``EOFError`` from an open connection is a real failure and is raised."""
    client, bus = make_connected_client()
    bus.call = AsyncMock(side_effect=EOFError)

    with pytest.raises(EOFError):
        await client.disconnect()

    bus.disconnect.assert_not_called()

# -*- coding: utf-8 -*-

import asyncio

from bleak.backends.bluezdbus.defs import PROPERTIES_INTERFACE, OBJECT_MANAGER_INTERFACE


def listen_properties_changed(bus, callback):
    """Create a future for a PropertiesChanged signal listener.

    Args:
        bus: The system bus object to use.
        callback: The callback function to run when signal is received.

    Returns:
        Integer rule id.

    """
    return bus.addMatch(
        callback,
        interface=PROPERTIES_INTERFACE,
        member="PropertiesChanged",
        path_namespace="/org/bluez",
    ).asFuture(asyncio.get_event_loop())


def listen_interfaces_added(bus, callback):
    """Create a future for a InterfacesAdded signal listener.

    Args:
        bus: The system bus object to use.
        callback: The callback function to run when signal is received.

    Returns:
        Integer rule id.

    """
    return bus.addMatch(
        callback,
        interface=OBJECT_MANAGER_INTERFACE,
        member="InterfacesAdded",
        path_namespace="/org/bluez",
    ).asFuture(asyncio.get_event_loop())


def listen_interfaces_removed(bus, callback):
    """Create a future for a InterfacesAdded signal listener.

    Args:
        bus: The system bus object to use.
        callback: The callback function to run when signal is received.

    Returns:
        Integer rule id.

    """
    return bus.addMatch(
        callback,
        interface=OBJECT_MANAGER_INTERFACE,
        member="InterfacesRemoved",
        path_namespace="/org/bluez",
    ).asFuture(asyncio.get_event_loop())

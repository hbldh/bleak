# -*- coding: utf-8 -*-

from bleak.backends.bluezdbus.defs import PROPERTIES_INTERFACE, OBJECT_MANAGER_INTERFACE


def listen_properties_changed(bus, loop, callback):
    """Create a future for a PropertiesChanged signal listener.

    Args:
        bus: The system bus object to use.
        loop: The asyncio loop to use for adding the future to.
        callback: The callback function to run when signal is received.

    Returns:
        Integer rule id.

    """
    return bus.addMatch(
        callback, interface=PROPERTIES_INTERFACE, member="PropertiesChanged"
    ).asFuture(loop)


def listen_interfaces_added(bus, loop, callback):
    """Create a future for a InterfacesAdded signal listener.

    Args:
        bus: The system bus object to use.
        loop: The asyncio loop to use for adding the future to.
        callback: The callback function to run when signal is received.

    Returns:
        Integer rule id.

    """
    return bus.addMatch(
        callback, interface=OBJECT_MANAGER_INTERFACE, member="InterfacesAdded"
    ).asFuture(loop)


def listen_interfaces_removed(bus, loop, callback):
    """Create a future for a InterfacesAdded signal listener.

    Args:
        bus: The system bus object to use.
        loop: The asyncio loop to use for adding the future to.
        callback: The callback function to run when signal is received.

    Returns:
        Integer rule id.

    """
    return bus.addMatch(
        callback, interface=OBJECT_MANAGER_INTERFACE, member="InterfacesRemoved"
    ).asFuture(loop)

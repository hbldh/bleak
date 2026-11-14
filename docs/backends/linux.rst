.. _linux-backend:

Linux backend
=============

The Linux backend of Bleak communicates with `BlueZ <http://www.bluez.org/>`_
over DBus. Communication uses the `dbus-fast
<https://github.com/Bluetooth-Devices/dbus-fast>`_ package for async access to
DBus messaging.


Resolving services with ``get_services``
----------------------------------------

By default, calling ``get_services`` will wait for services to be resolved
before returning the ``BleakGATTServiceCollection``. If a previous connection
to the device was made, passing the ``dangerous_use_bleak_cache`` argument will
return the cached services without waiting for them to be resolved again. This
is useful when you know services have not changed, and you want to use the
services immediately, but don't want to wait for them to be resolved again.

.. _linux-start-notify:

Enabling notification/indication with ``start_notify``
------------------------------------------------------
BlueZ has two different methods of subscribing to notifications/indications:
"StartNotify" and "AcquireNotify". For best compatibility, Bleak defaults to
using "StartNotify". However, in cases where there is a characteristic that
needs to be read after the notification is received to get the full data, using
"AcquireNotify" is recommended to avoid receiving notifications for the both
the notification and the read operation. To do this, pass ``bluez={"use_start_notify": False}``.
to ``start_notify``.

Briefly, in Bleak v3.0.0 and v3.0.1, "AcquireNotify" was used by default, but
this caused issues with a number of devices, so the default was changed back to
"StartNotify". If you have an affected device and need to support these versions
of Bleak, you can set ``bluez={"use_start_notify": True}`` to make it work on
all versions of Bleak.


MTU size
--------

BlueZ >= 5.62 provides the negotiated ATT MTU in the "MTU" property of each
characteristic, which ``BleakClient.mtu_size`` reads. Older versions of BlueZ
do not provide the MTU, so ``mtu_size`` logs a warning and returns the default
value of 23.

Older versions of Bleak needed the private ``_acquire_mtu()`` method to be
called before reading ``mtu_size``. It is now deprecated and does nothing. To
support older versions of Bleak without the deprecation warning, only call it
when the ``_mtu_size`` attribute exists::

    if hasattr(client._backend, "_mtu_size"):
        await client._backend._acquire_mtu()


Parallel Access
---------------

Each Bleak object should be created and used from a single `asyncio event
loop`_. Simple asyncio programs will only have a single event loop. It's also
possible to use Bleak with multiple event loops, even at the same time, but
individual Bleak objects should not be shared between event loops. Otherwise,
RuntimeErrors similar to ``[...] got Future <Future pending> attached to a
different loop`` will be thrown.

D-Bus Authentication
--------------------

Connecting to the host DBus from within a user namespace will fail. This is
because the remapped UID will not match the UID that the hosts sees. To work
around this, you can hardcode a UID with the `BLEAK_DBUS_AUTH_UID` environment
variable.


API
---

Scanner
~~~~~~~

.. automodule:: bleak.backends.bluezdbus.scanner
    :members:

Client
~~~~~~

.. automodule:: bleak.backends.bluezdbus.client
    :members:

.. _`asyncio event loop`: https://docs.python.org/3/library/asyncio-eventloop.html

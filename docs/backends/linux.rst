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

.. _linux-backend:

Linux backend
=============

The Linux backend of Bleak is written using the
`TxDBus <https://github.com/cocagne/txdbus>`_
package. It is written for
`Twisted <https://twistedmatrix.com/trac/>`_, but by using the
`twisted.internet.asyncioreactor <https://twistedmatrix.com/documents/current/api/twisted.internet.asyncioreactor.html>`_
one can use it with `asyncio`.


Special handling for ``write_gatt_char``
----------------------------------------

The ``type`` option to the ``Characteristic.WriteValue``
method was added to
`Bluez in 5.51 <https://git.kernel.org/pub/scm/bluetooth/bluez.git/commit?id=fa9473bcc48417d69cc9ef81d41a72b18e34a55a>`_
Before that commit, ``Characteristic.WriteValue`` was only "Write with response".

``Characteristic.AcquireWrite`` was added in
`Bluez 5.46 <https://git.kernel.org/pub/scm/bluetooth/bluez.git/commit/doc/gatt-api.txt?id=f59f3dedb2c79a75e51a3a0d27e2ae06fefc603e>`_
which can be used to "Write without response", but for older versions of Bluez (5.43, 5.44, 5.45), it is not possible to "Write without response".

Resolving services with ``get_services``
----------------------------------------

By default, calling ``get_services`` will wait for services to be resolved
before returning the ``BleakGATTServiceCollection``. If a previous connection
to the device was made, passing the ``dangerous_use_bleak_cache`` argument will
return the cached services without waiting for them to be resolved again. This
is useful when you know services have not changed, and you want to use the
services immediately, but don't want to wait for them to be resolved again.


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

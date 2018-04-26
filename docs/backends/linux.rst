Linux backend
=============

The Linux backend of bleak is written using the `TxDBus <https://github.com/cocagne/txdbus>`_
package. It is written for `Twisted <https://twistedmatrix.com/trac/>`_, but by using the
`twisted.internet.asyncioreactor <https://twistedmatrix.com/documents/current/api/twisted.internet.asyncioreactor.html>`_ one can use it in the `asyncio` way.

API
---

Read more about the BlueZ DBus API `here <https://git.kernel.org/pub/scm/bluetooth/bluez.git/tree/doc>`_.

The relevant documents for this project are `adapter-api.txt`, `device-api.txt` and `gatt-api.txt`.

Discover
~~~~~~~~

.. automodule:: bleak.backends.bluezdbus.discovery
    :members:

Client
~~~~~~

.. automodule:: bleak.backends.bluezdbus.client
    :members:

===================
Usage and Tutorials
===================

Basic recommendations for using Bleak:

1.  When running applications with Bleak, always use ``asyncio.run`` (`See Python documentation <https://docs.python.org/3/library/asyncio-task.html#asyncio.run>`_) to start the main
    method if you are running Python >= 3.7. If you are on Python 3.6, then you have to take some extra care to
    make sure Bleak exists properly. See `this example <#>`_ for details on how to do that.
2.  Try using the async context manager for creating and connecting with
    :class:`<BleakClient> bleak.backends.client.BleakClient` if possible, rather than handling it yourself. That
    will ensure a clean and complete disconnection.
3.  If you are not familiar with asynchronous programming and `asyncio` in Python, go through a tutorial on that
    to learn how to use it first. This one on `Real Python <https://realpython.com/async-io-python/>`_ is a good primer.

.. note::

    A Bluetooth peripheral may have several characteristics with the same UUID, so
    the means of specifying characteristics by UUID or string representation of it
    might not always work in bleak version > 0.7.0. One can now also use the characteristic's
    handle or even the ``BleakGATTCharacteristic`` object itself in
    ``read_gatt_char``, ``write_gatt_char``, ``start_notify``, and ``stop_notify``.


Contents:

.. toctree::
   :maxdepth: 1

   scanning
   connect
   reading
   writing
   notifications
   pairing
   reconnect
   sigspec



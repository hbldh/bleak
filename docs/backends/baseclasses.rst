Creating new backends
=====================

If you want to create a new backend, for a platform that is not supported yet, you must create subclasses
for all the classes below. Unlike most abstract API classes, as presented to users, the base classes have
constructors that you must call when you create the object. There are also additional methods in the baseclasses, 
for example to populate a service with its characteristics. While these methods _are_ technically available in the API
that is presented to end users (Python has no way to create friend classes or hide superclass methods) they are
discouraged to call these methods. That does not hold for you.

Implementation base classes
---------------------------

.. automodule:: bleak.backends.scanner
    :members:

.. automodule:: bleak.backends.client
    :members:

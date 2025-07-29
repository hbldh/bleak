.. highlight:: shell

============
Installation
============


Stable release
--------------

To install bleak, run this command in your terminal:

.. code-block:: console

    $ pip install bleak

This is the preferred method to install bleak, as it will always install the most recent stable release.

If you don't have `pip`_ installed, this `Python installation guide`_ can guide
you through the process.

.. _pip: https://pip.pypa.io
.. _Python installation guide: http://docs.python-guide.org/en/latest/starting/installation/


Develop branch
--------------

The develop branch can also be installed using ``pip``. This is useful for
testing the latest changes before they reach the stable release.

.. code-block:: console

    $ pip install https://github.com/hbldh/bleak/archive/refs/heads/develop.zip

For checking out a copy of Bleak for developing Bleak itself, see the :doc:`contributing` page.


Pythonista iOS app
^^^^^^^^^^^^^^^^^^
Use `StaSh <https://github.com/ywangd/stash>`_
or `Pythonista3_pip_Configration_Tool <https://github.com/CrossDarkrix/Pythonista3_pip_Configration_Tool>`_ for pip

.. code-block:: console

    $ pip install bleak[pythonista]

It should install ``bleak`` and ``bleak-pythonista``
Then use bleak as common :doc:`usage` or refer to `bleak-pythonista docs <https://github.com/o-murphy/bleak-pythonista/blob/master/docs/pythonista.rst>`_

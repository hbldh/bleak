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

Development version
-------------------

If you want to install the latest development version of Bleak, without cloning the repository and
setting up a development environment:

.. code-block::

    pip install --force-reinstall https://github.com/hbldh/bleak/archive/develop.zip#egg=bleak


From sources
------------

The sources for bleak can be downloaded from the `Github repo`_.

You can either clone the public repository:

.. code-block:: console

    $ git clone git://github.com/hbldh/bleak

Or download the `tarball`_:

.. code-block:: console

    $ curl  -OL https://github.com/hbldh/bleak/tarball/master

Once you have a copy of the source, you can install it with:

.. code-block:: console

    $ python setup.py install


.. _Github repo: https://github.com/hbldh/bleak
.. _tarball: https://github.com/hbldh/bleak/tarball/master

Integration tests
-----------------

This folder contains integration tests for bleak.

Hardware in the loop
~~~~~~~~~~~~~~~~~~~~

To run these tests, you need two Bluetooth controllers. One that is connected to
your OS (e.g. the builtin Bluetooth adapter of your PC/laptop) and controlled by
``bleak``. And one to use as a Bluetooth peripheral device that is controlled
via ``bumble``. These two need to be near to each other, so that they are in
receive range to each other.

The peripheral device can theoretically be any Bluetooth HCI controller supported
by ``bumble``. Currently the tested option is via an `nRF52840 Dongle <https://www.nordicsemi.com/Products/Development-hardware/nRF52840-Dongle>`_
with a HCI-UART firmware. The firmware including instructions can be found
`here <https://github.com/timrid/ble-dongle-firmware>`_. The HCI-UART firmware has
the advantage over the HCI-USB firmware, that it is not automatically claimed by
the OS, so that ``bumble`` can use it without special configurations.

To run the integration tests you have to pass the ``--bleak-hci-transport`` moniker of your
 ``bumble`` device. You have to specify the bumble moniker of the transport. For more
information see the `bumble documentation <https://google.github.io/bumble/transports/serial.html>`_.

It looks for example like this on macOS::

    $ uv run pytest --bleak-hci-transport=serial:/dev/tty.usbmodem1101

On macOS you can find the port via::

    $ ls /dev/tty.usbmodem*

On Linux::

    # ls /dev/ttyACM*

On Windows you can find the port via the Device Manager under "Ports (COM & LPT)".
And the moniker will look like this::

    serial:COM3


Virtual Bluetooth controllers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

An alternative to using physical hardware is to use virtual Bluetooth controllers created
by ``bumble`` and connected to your OS via a VHCI interface: ``/dev/vhci`` on Linux with
BlueZ, the ``winvhci`` driver on Windows. This virtual controller replaces the builtin
Bluetooth adapter of your PC/laptop from the previous chapter. This Bluetooth controller
is then controlled by ``bleak``.

Then a second virtual Bluetooth controller can be created with ``bumble`` that connects
to the first virtual controller through a so called `LocalLink`. This is like a virtual
RF link between multiple virtual controllers. This second virtual controller acts as the
peripheral device and replaces the nRF Dongle from the previous chapter.

This way you can run integration tests without any physical hardware, just using virtual
Bluetooth controllers. To use this setup you have to use the additional command line option
``--bleak-vhci`` to run the tests::

    $ uv run pytest --bleak-vhci

``--bleak-bluez-vhci`` is a deprecated alias for the same option, from when BlueZ was the
only stack that could be driven this way.

Linux (BlueZ)
^^^^^^^^^^^^^

You may need to load the kernel module first::

    $ sudo modprobe hci_vhci

To run the tests without root privileges, you have to give your current user access to VHCI.

On Ubuntu this can be done by adding your user to the ``bluetooth`` group::

    $ sudo groupadd bluetooth  # should already exist
    $ sudo usermod -aG bluetooth $USER
    $ echo 'KERNEL=="vhci", GROUP="bluetooth", MODE="0660"' | sudo tee /etc/udev/rules.d/99-vhci.rules
    $ sudo udevadm control --reload-rules  # usually this is done automatically
    $ sudo udevadm trigger --sysname-match vhci

If you weren't already in the ``bluetooth`` group, then you need to reload your
group membership. Either log out and log back in, or run::

    $ newgrp bluetooth  # warning, this will start a new shell

Windows
^^^^^^^

Windows has no ``/dev/vhci``, so the virtual controller is provided by the `winvhci
<https://github.com/dlech/windows-vhci-driver>`_ driver: a kernel driver that presents a
virtual Bluetooth radio which the in-box Windows Bluetooth stack binds to and treats as
real hardware. Install the release matching the ``winvhci`` requirement in
``pyproject.toml``, then run its installer from an elevated prompt::

    PS> .\install-winvhci.ps1

The driver is test-signed, so the machine needs test signing on, Secure Boot off and
memory integrity off. The installer names any missing prerequisite and refuses rather
than half-installing, and ``-Uninstall`` removes everything it added. Because those
settings weaken the machine, run the tests in a VM or on a dedicated test machine rather
than on a daily driver.

Nothing has to be started by hand: the radio's lifetime is the lifetime of an open handle
to the driver, so the test fixture creates it and Windows removes it again when the
fixture closes.

Bleak uses whichever adapter WinRT reports as the default, which is not necessarily the
virtual one. If a real radio wins that election the fixture fails with an error naming
both addresses, so disable any physical Bluetooth adapter before running the tests.

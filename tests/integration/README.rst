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

An alternative to using physical hardware on Linux with BlueZ is to use virtual Bluetooth
controllers created by ``bumble`` and connected to your OS via the VHCI interface. This
virtual controller replaces the builtin Bluetooth adapter of your PC/laptop from the
previous chapter. This Bluetooth controller is then controlled by ``bleak``.

Then a second virtual Bluetooth controller can be created with ``bumble`` that connects
to the first virtual controller through a so called `LocalLink`. This is like a virtual
RF link between multiple virtual controllers. This second virtual controller acts as the
peripheral device and replaces the nRF Dongle from the previous chapter.

This way you can run integration tests without any physical hardware, just using virtual
Bluetooth controllers. To use this setup you have to use the additional command line option
``--bleak-bluez-vhci`` to run the tests::

    $ uv run pytest --bleak-bluez-vhci

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


Android
~~~~~~~

The Android backend integration tests are run inside a dedicated Android testbed app that
executes the pytest test suite directly on the device. This app is generated with
`Briefcase <https://briefcase.beeware.org/en/stable/>`_ and can be found in the 
``examples/briefcase`` folder.

Tests can be run either on a real Android device or on an emulator.

Real Device
^^^^^^^^^^^

To run the integration tests on a real device, connect the nRF52840 Dongle to the host PC
and start the tests with the following command. The script starts a TCP server that transparently
forwards data to and from the serial port of the dongle, and sets up an ADB
reverse-port tunnel so that the Android device can reach that TCP server. This allows the
tests running on the Android device to communicate with the dongle over Bluetooth::

    $ uv run examples/briefcase/run_android_tests_real_device.py --bleak-hci-transport=serial:/dev/tty.usbmodem11401

.. note::

   Some tests (permissions, pairing) will show system dialogs on the Android device that
   must be confirmed manually.

Emulator
^^^^^^^^

The integration tests can also be run entirely without physical hardware using the Android
Emulator together with Android's built-in Bluetooth simulator (netsim). System dialogs for
Bluetooth permissions and pairing are automatically confirmed via ADB
automation, so the tests run without any manual interaction. This setup works
headlessly, for example in GitHub Actions.

::

    $ uv run examples/briefcase/run_android_tests_emulator.py

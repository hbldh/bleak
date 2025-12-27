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

To run the integration tests you have to pass the ``--bleak-hci-transport`` monkier of your
 ``bumble`` device. You have to specify the bumble moniker of the transport. For more
information see the `bumble documentation <https://google.github.io/bumble/transports/serial.html>`_.

It looks for example like this on macOS:

    $ poetry run pytest --bleak-hci-transport=serial:/dev/tty.usbmodem1101

On macOS you can find the port via:
    
    $ ls /dev/tty.usbmodem*



Virtual Bluetooth controllers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

An alternative to using physical hardware on Linux with BlueZ is to use virtual Bluetooth
controllers created by ``bumble`` and connected to your OS via the VHCI interface. This
virtual controller replaces the builtin Bluetooth adapter of your PC/laptop from the 
previous chapter. This Bluetooth controller is then controlled by ``bleak``.

Then a secound virtual Bluetooth controller can be created with ``bumble`` that connects
to the first virtual controller through a so called `LocalLink`. This is like a virtual
RF link between multiple virtual controllers. This second virtual controller acts as the
peripheral device and replaces the nRF Dongle from the previous chapter.

This way you can run integration tests without any physical hardware, just using virtual
Bluetooth controllers. To use this setup you have to use the additional command line option
``--bleak-bluez-vhci`` to run the tests:

    $ poetry run pytest --bleak-bluez-vhci

To run the tests without root privileges, you have to give your current user access to VHCI.

On Ubuntu this can be done by adding your user to the ``bluetooth`` group:

    $ sudo groupadd bluetooth
    $ sudo usermod -aG bluetooth $USER
    $ echo 'KERNEL=="vhci", GROUP="bluetooth", MODE="0666"' | sudo tee /etc/udev/rules.d/99-vhci.rules
    $ sudo udevadm control --reload-rules
    $ sudo udevadm trigger

After that you have to log out and log back in for the group change to take effect.
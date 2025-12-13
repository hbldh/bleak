Integration tests
-----------------

This folder contains integration tests for bleak.

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




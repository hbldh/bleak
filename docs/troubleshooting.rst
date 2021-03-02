===============
Troubleshooting
===============

When things don't seem to be working right, here are some things to try.


--------------
Enable Logging
--------------

The easiest way to enable logging is to set the ``BLEAK_LOGGING`` environment variable.
Setting the variable depends on what type of terminal you are using.

Posix (Linux, macOS, Cygwin, etc.)::

    export BLEAK_LOGGING=1

Power Shell::

    $env:BLEAK_LOGGING=1

Windows Command Prompt::

    set BLEAK_LOGGING=1

Then run your Python script in the same terminal.


-------------------------
Capture Bluetooth Traffic
-------------------------

Sometimes it can be helpful to see what is actually going over the air between
the OS and the Bluetooth device. There are tools available to capture HCI packets
and decode them.

Windows 10
==========

No special software is required on Windows to capture Bluetooth traffic, however
special software is required to convert it to a useful format.

Capture
-------

To capture Bluetooth traffic:

1.  Open a Command Prompt as Administrator.

    * Search start menu for ``cmd``.
    * Right-click *Command Prompt* and select *Run as Administrator*.

      .. image:: images/win-10-start-cmd-as-admin.png
        :height: 200px
        :alt: Screenshot of Windows Start Menu showing Command Prompt selected
              and context menu with Run as Administrator selected.

2.  Run the following command in the Administrator Command Prompt::

        logman create trace "bth_hci" -ow -o C:\bth_hci.etl -p {8a1f9517-3a8c-4a9e-a018-4f17a200f277} 0xffffffffffffffff 0xff -nb 16 16 -bs 1024 -mode Circular -f bincirc -max 4096 -ets

    .. tip:: ``C:\bth_hci.etl`` can be replaced with any file path you like.

3.  Run your Python script in a different terminal (not as Administrator) to reproduce
    the problem.

4.  In the Administrator Command Prompt run::

        logman stop "bth_hci" -ets


Decode
------

Microsoft no longer has tools to directly view ``.etl`` files so in order to
make use of the information, we need to convert it to a different file format.
The `Windows Driver Kit <wdk_>`_ contains a tool to do this.

.. _wdk: https://docs.microsoft.com/en-us/windows-hardware/drivers/download-the-wdk

1.  Download and install the  `Windows Driver Kit <wdk_>`_.

    .. tip:: The install may give warnings about additional software not being
             installed. These warnings can be ignored since we just need a standalone
             executable file from the installation.

2.  Run the following command::

        "%ProgramFiles(x86)%\Windows Kits\10\Tools\x86\Bluetooth\BETLParse\btetlparse.exe" c:\bth_hci.etl

    This will create a file with the same file name and a ``.cfa`` file extension
    (and an empty ``.txt`` file for some reason).

3.  Download and install `Wireshark`_.

4.  Open the ``.cfa`` file in Wireshark to view the captured Bluetooth traffic.


.. _Wireshark:  https://www.wireshark.org/


macOS
=====

On macOS, special software is required to capture and view Bluetooth traffic.
You will need to sign up for an Apple Developer account to obtain this software.

1.  Go to `<https://developer.apple.com/download/more/>`_ and download *Additional
    Tools for Xcode ...* where ... is the Xcode version corresponding to your macOS
    version (e.g. 12 for Big Sur, 11 for Mojave, etc.).

2.  Open the disk image and in the *Hardware* folder, double-click the *PacketLogger.app*
    to run it.

3.  Click the *Clear* button in the toolbar to clear the old data.

4.  Run your Python script to reproduce the problem.

5.  Click the *Stop* button in the toolbar to stop the capture.

.. tip:: The Bluetooth traffic can be viewed in the *PacketLogger.app* or it can
         be saved to a file and viewed in `Wireshark`_.


Linux
=====

On Linux, `Wireshark`_ can be used to capture and view Bluetooth traffic.

1.  Install Wireshark. Most distributions include a ``wireshark`` package. For
    example, on Debian/Ubuntu based distributions::

        sudo apt update && sudo apt install wireshark

2.  Start Wireshark and select your Bluetooth adapter, then start a capture.

    .. tip:: Visit the `Wireshark Wiki`_ for help with configuring permissions
             and making sure proper drivers are installed.

3.  Run your Python script to reproduce the problem.

4.  Click the stop button in Wireshark to stop the capture.


.. _Wireshark Wiki: https://gitlab.com/wireshark/wireshark/-/wikis/CaptureSetup


------------------------------------------
Handling OS Caching of BLE Device Services
------------------------------------------

If you develop your own BLE peripherals, and frequently change services, characteristics and/or descriptors, then
Bleak might report outdated versions of your peripheral's services due to OS level caching. The caching is done to
speed up the connections with peripherals where services do not change and is enabled by default on most operating
systems and thus also in Bleak.

There are ways to avoid this on different backends though, and if you experience these kinds of problems, the steps
below might help you to circumvent the caches.

Windows 10
==========

The Windows .NET backend has the most straightforward means of handling the os caches. When creating a BleakClient, one
can use the keyword argument `use_cached`:

.. code-block:: python

    async with BleakClient(address, use_cached=False) as client:
        print(f"Connected: {client.is_connected}")
        // Do whatever it is you want to do.

The keyword argument is also present in the :py:meth:`bleak.backends.client.BleakClient.connect` method to use if you
don't want to use the async context manager:

.. code-block:: python

    client = BleakClient(address)
    await client.connect(use_cached=True)
    print(f"Connected: {client.is_connected}")
    // Do whatever it is you want to do.
    await client.disconnect()

macOS
=====

The OS level caching handling on macOS has not been explored yet.


Linux
=====

When you change the structure of services/characteristics on a device, you have to remove the device from
BlueZ so that it will read everything again. Otherwise BlueZ gives the cached values from the first time
the device was connected. You can use the ``bluetoothctl`` command line tool to do this:

.. code-block:: shell

    bluetoothctl -- remove [mac_address]


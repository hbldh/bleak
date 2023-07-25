=========
Changelog
=========

All notable changes to this project will be documented in this file.

The format is based on `Keep a Changelog <https://keepachangelog.com/en/1.0.0/>`_,
and this project adheres to `Semantic Versioning <https://semver.org/spec/v2.0.0.html>`_.

`Unreleased`_
=============

Added
-----
* Added ``bleak.uuids.normalize_uuid_16()`` function.
* Added ``bleak.uuids.normalize_uuid_32()`` function.
* Added ``advertisement_data()`` async iterator method to ``BleakScanner``. Merged #1361.

Changed
-------
* Improved error messages when failing to get services in WinRT backend.
* Improved error messages with enum values in WinRT backend. Fixes #1284.
* Scanner backends modified to allow multiple advertisement callbacks. Merged #1367.
* Changed default handling of the ``response`` argument in ``BleakClient.write_gatt_char``.
  Fixes #909.

Fixed
-----
* Fixed handling all access denied errors when enumerating characteristics on Windows. Fixes #1291.
* Added support for 32bit UUIDs. Fixes #1314.
* Fixed typing for ``BaseBleakScanner`` detection callback.
* Fixed possible crash in ``_stopped_handler()`` in WinRT backend. Fixes #1330.
* Reduced expensive logging in the BlueZ backend. Merged #1376.

`0.20.2`_ (2023-04-19)
======================

Fixed
-----
* Fixed ``org.bluez.Error.InProgress`` in characteristic and descriptor read and
  write methods in BlueZ backend.
* Fixed ``OSError: [WinError -2147483629] The object has been closed`` when
  connecting on Windows. Fixes #1280.

`0.20.1`_ (2023-03-24)
======================

Fixed
-----
* Fixed possible garbage collection of running async callback from ``BleakClient.start_notify()``.
* Fixed possible garbage collection of running async callback from ``BleakScanner(detection_callback=)``.
* Fixed possible garbage collection of disconnect monitor in BlueZ backend. Fixed #1258.

`0.20.0`_ (2023-03-17)
======================

Added
-----
* Added ``BLEAK_DBUS_AUTH_UID`` environment variable for hardcoding D-Bus UID. Merged #1182.
* Added return type ``None`` to some scanner methods.
* Added optional hack to use Bluetooth address instead of UUID on macOS. Merged #1073.
* Added ``BleakScanner.find_device_by_name()`` class method.
* Added optional command line argument to use debug log level to all applicable examples.
* Added ``bleak.uuids.normalize_uuid_str()`` function.
* Added optional ``services`` argument to ``BleakClient()`` to filter services. Merged #654.
* Added automatic retry on ``le-connection-abort-by-local`` in BlueZ backend. Fixes #1220.

Changed
-------
* Dropped ``async-timeout`` dependency on Python >= 3.11.
* Deprecated ``BLEDevice.rssi`` and ``BLEDevice.metadata``. Fixes #1025.
* ``BLEDevice`` now uses ``__slots__`` to reduce memory usage. Merged #1117.
* ``BaseBleakClient.services`` is now ``None`` instead of empty service collection
  until services are discovered.
* Include thread name in ``BLEAK_LOGGING`` output. Merged #1144.
* Updated PyObjC dependency on macOS to v9.x.

Fixed
-----
* Fixed invalid UTF-8 in ``uuids.uuid16_dict``.
* Fixed ``AttributeError`` in ``_ensure_success`` in WinRT backend.
* Fixed ``BleakScanner.stop()`` can raise ``BleakDBusError`` with ``org.bluez.Error.NotReady`` in BlueZ backend.
* Fixed ``BleakScanner.stop()`` hanging in WinRT backend when Bluetooth is disabled.
* Fixed leaking services when ``get_services()`` is cancelled in WinRT backend.
* Fixed disconnect monitor task not always cancelled on the BlueZ client. Merged #1159.
* Fixed WinRT scanner never calling ``detection_callback`` when a device does
  not send a scan response. Fixes #1211.
* Fixed ``BLEDevice`` name sometimes incorrectly ``None``.
* Fixed unhandled exception in ``CentralManagerDelegate`` destructor on macOS. Fixes #1219.
* Fixed object passed to ``disconnected_callback`` is not ``BleakClient``. Fixes #1200.

`0.19.5`_ (2022-11-19)
======================

Fixed
-----
* Fixed more issues with getting services in WinRT backend.


`0.19.4`_ (2022-11-06)
======================

Fixed
-----
* Fixed ``TypeError`` in WinRT backend introduced in v0.19.3.


`0.19.3`_ (2022-11-06)
======================

Fixed
-----
* Fixed ``TimeoutError`` when connecting to certain devices with WinRT backend. Fixes #604.


`0.19.2`_ (2022-11-06)
======================

Fixed
------
* Fixed crash when getting services in WinRT backend in Python 3.11. Fixes #1112.
* Fixed cache mode when retrying get services in WinRT backend. Merged #1102.
* Fixed ``KeyError`` crash in BlueZ backend when removing non-existent property. Fixes #1107.

`0.19.1`_ (2022-10-29)
======================

Fixed
-----
* Fixed crash in Android backend introduced in v0.19.0. Fixes #1085.
* Fixed service discovery blocking forever if device disconnects in BlueZ backend. Merged #1092.
* Fixed ``AttributeError`` crash when scanning on Windows builds < 19041. Fixes #1094.

`0.19.0`_ (2022-10-13)
======================

Added
-----
* Added support for Python 3.11. Merged #990.
* Added better error message for Bluetooth not authorized on macOS. Merged #1033.
* Added ``BleakDeviceNotFoundError`` which should is raised if a device can not
  be found by ``connect``, ``pair`` and ``unpair``. Merged #1022.
* Added ``rssi`` attribute to ``AdvertisementData``. Merged #1047.
* Added ``BleakScanner.discovered_devices_and_advertisement_data`` property. Merged #1047.
* Added ``return_adv`` argument to ``BleakScanner.discover`` method. Merged #1047.
* Added ``BleakClient.unpair()`` implementation for BlueZ backend. Merged #1067.

Changed
-------
* Changed ``AdvertisementData`` to a named tuple. Merged #1047.
* A faster ``unpack_variants`` is now provided by dbus-fast. Merged #1055.

Fixed
-----
* On BlueZ, support creating additional instances running on a different event
  loops (i.e. multiple pytest-asyncio cases). Merged #1034.
* Fixed unhandled exception in ``max_pdu_size_changed_handler`` in WinRT backend. Fixes #1039.
* Fixed stale services in WinRT backend causing ``WinError -2147483629``. Fixes #1061.

Removed
-------
Removed ``bleak.__version__``. Use ``importlib.metadata.version('bleak')`` instead.

`0.18.1`_ (2022-09-25)
======================

Fixed
-----
* Reverted unintentional breaking parameter name changes. Fixes #1028.


`0.18.0`_ (2022-09-23)
======================

Changed
-------
* Relaxed ``async-timeout`` dependency version to support different installations. Merged #1009.
* ``BleakClient.unpair()`` in WinRT backend can be called without being connected first. Merged #1012.
* Use relative imports internally. Merged #1007.
* ``BleakScanner`` and ``BleakClient`` are now concrete classes. Fixes #582.
* Deprecated ``BleakScanner.register_detection_callback()``.
* Deprecated ``BleakScanner.set_scanning_filter()``.
* Deprecated ``BleakClient.set_disconnected_callback()``.
* Deprecated ``BleakClient.get_services()``.
* Refactored common code in ``BleakClient.start_notify()``.
* (BREAKING) Changed notification callback argument from ``int`` to ``BleakGattCharacteristic``. Fixes #759.

Fixed
-----
* Fixed ``tx_power`` not included in ``AdvertisementData.__repr__`` when 0. Merged #1017.

`0.17.0`_ (2022-09-12)
======================

Added
-----
* ``AdvertisementData`` class now has an attribute ``tx_power``. Merged #987.

Changed
-------
* ``BleakClient`` methods now raise ``BleakError`` if called when not connected in WinRT backend. Merged #973.
* Extended disconnect timeout to 120 seconds in WinRT backend. Fixes #807.
* Changed version check for BlueZ battery workaround to exclude versions >= 5.55. Merged #976.
* Use Poetry for build system and dependencies. Merged #978.
* The BlueZ D-Bus backend implements a services cache between connections to significancy improve reconnect performance.
  To use the cache, call ``connect`` and ``get_services`` with the ``dangerous_use_bleak_cache``
  argument to avoid services being resolved again. Merged #923.
* The BlueZ D-Bus backend now uses ``dbus-fast`` package instead of ``dbus-next`` which significantly improves performance. Merged #988.
* The BlueZ D-Bus backend will not avoid trying to connect to devices that are already connected. Fixes #992.
* Updated logging to lazy version and replaced format by f-string for ``BleakClientWinRT``. #1000.
* Added deprecation warning to ``discover()`` method. Merged #1005.
* BlueZ adapter is chosen dynamically if not provided, instead of using hardcoded "hci0". Fixes #513.

Fixed
-----
* Fixed wrong error message for BlueZ "Operation failed with ATT error". Merged #975.
* Fixed possible ``AttributeError`` when enabling notifications for battery service in BlueZ backend. Merged #976.
* Fixed use of wrong enum in unpair function of WinRT backend. Merged #986.
* Fixed inconsistent return types for ``properties`` and ``descriptors`` properties of ``BleakGATTCharacteristic``. Merged #989.
* Handle device being removed before ``GetManagedObjects`` returns in BlueZ backend. Fixes #996.
* Fixed crash in ``max_pdu_size_changed_handler`` in WinRT backend. Fixes #998.
* Fixes a race in the BlueZ D-Bus backend where the disconnect monitor would be removed before it could be awaited. Merged #999.

Removed
-------
* Removed ``BLEDeviceCoreBluetooth`` type from CoreBluetooth backend. Merged #977.

`0.16.0`_ (2022-08-31)
======================

Added
-----
* Added ``BleakGattCharacteristic.max_write_without_response_size`` property. Fixes #738.

Fixed
-----
* Fixed regression in v0.15 where devices removed from BlueZ while scanning
  were still listed in ``BleakScanner.discovered_devices``. Fixes #942.
* Fixed possible bad connection state in BlueZ backend. Fixes #951.

Changed
-------
* Made BlueZ D-Bus signal callback logging lazy to improve performance. Merged #912.
* Switch to using ``async_timeout`` instead of ``asyncio.wait_for for performance``. Merged #916.
* Improved performance of ``BlueZManager.get_services()``. Fixes #927.

Removed
-------
* Removed explicit inheritance from object in class declarations. Merged #922.
* Removed first seen filter in ``BleakScanner`` detection callbacks on BlueZ backend. Merged #964.

`0.15.1`_ (2022-08-03)
======================

Fixed
-----
* The global BlueZ manager now disconnects correctly on exception. Merged #918.
* Handle the race in the BlueZ D-Bus backend where the device disconnects during
  the connection process which presented as ``Failed to cancel connection``. Merged #919.
* Ensure the BlueZ D-Bus scanner can reconnect after DBus disconnection. Merged #920.
* Adjust default timeout for ``read_gatt_char()`` with CoreBluetooth to 20s. Fixes #926.


`0.15.0`_ (2022-07-29)
======================

Added
-----

* Added new ``assigned_numbers`` module and ``AdvertisementDataType`` enum.
* Added new ``bluez`` kwarg to ``BleakScanner`` in BlueZ backend.
* Added support for passive scanning in the BlueZ backend. Fixes #606.
* Added option to use cached services, characteristics and descriptors in WinRT backend. Fixes #686.
* Added ``PendingDeprecationWarning`` to use of ``address_type`` as keyword argument. It will be moved into the
  ``winrt`` keyword instead according to #623.
* Added better error message when adapter is not present in BlueZ backend. Fixes #889.

Changed
-------

* Add ``py.typed`` file so mypy discovers Bleak's type annotations.
* UUID descriptions updated to 2022-03-16 assigned numbers document.
* Replace use of deprecated ``asyncio.get_event_loop()`` in Android backend.
* Adjust default timeout for ``read_gatt_char()`` with CoreBluetooth to 10s. Merged #891.
* ``BleakScanner()`` args ``detection_callback`` and ``service_uuids`` are no longer keyword-only.
* ``BleakScanner()`` arg ``scanning_mode`` is no longer Windows-only and is no longer keyword-only.
* All ``BleakScanner()`` instances in BlueZ backend now use common D-Bus object manager.
* Deprecated ``filters`` kwarg in ``BleakScanner`` in BlueZ backend.
* BlueZ version is now checked on first connection instead of import to avoid import side effects. Merged #907.

Fixed
-----

* Documentation fixes.
* On empty characteristic description from WinRT, use the lookup table instead of returning empty string.
* Fixed detection of first advertisement in BlueZ backend. Merged #903.
* Fixed performance issues in BlueZ backend caused by calling "GetManagedObjects" each time a
  ``BleakScanner`` scans or ``BleakClient`` is connected. Fixes #500.
* Fixed not handling "InterfacesRemoved" in ``BleakClient`` in BlueZ backend. Fixes #882.
* Fixed leaking D-Bus socket file descriptors in BlueZ backend. Fixes #805.

Removed
-------

* Removed fallback to call "ConnectDevice" when "Connect" fails in Bluez backend. Fixes #806.

`0.14.3`_ (2022-04-29)
======================

Changed
-------

* Suppress macOS 12 scanner bug error message for macOS 12.3 and higher. Fixes #720.
* Added filters ``Discoverable`` and ``Pattern`` to BlueZ D-Bus scanner. Fixes #790.

Fixed
-----

* Fixed reading the battery level returns a zero-filled ``bytearray`` on BlueZ >= 5.48. Fixes #750.
* Fixed unpairing does not work on windows with WinRT. Fixes #699
* Fixed leak of ``_disconnect_futures`` in ``CentralManagerDelegate``.
* Fixed callback not removed from ``_disconnect_callbacks`` on disconnect in ``CentralManagerDelegate``.


`0.14.2`_ (2022-01-26)
======================

Changed
-------

* Updated ``bleak-winrt`` dependency to v1.1.1. Fixes #741.

Fixed
-----

* Fixed ``name`` is ``'Unknown'`` in WinRT backend. Fixes #736.


`0.14.1`_ (2022-01-12)
======================

Fixed
-----

* Fixed ``AttributeError`` when passing ``BLEDevice`` to ``BleakClient``
  constructor on WinRT backend. Fixes #731.


`0.14.0`_ (2022-01-10)
======================

Added
-----

* Added ``service_uuids`` kwarg to  ``BleakScanner``. This can be used to work
  around issue of scanning not working on macOS 12. Fixes #230. Works around #635.
* Added UUIDs for LEGO Powered Up Smart Hubs.

Changed
-------

* Changed WinRT backend to use GATT session status instead of actual device
  connection status.
* Changed handling of scan response data on WinRT backend. Advertising data
  and scan response data is now combined in callbacks like other platforms.
* Updated ``bleak-winrt`` dependency to v1.1.0. Fixes #698.

Fixed
-----

* Fixed ``InvalidStateError`` in CoreBluetooth backend when read and notification
  of the same characteristic are used. Fixes #675.
* Fixed reading a characteristic on CoreBluetooth backend also triggers notification
  callback.
* Fixed in Linux, scanner callback not setting metadata parameters. Merged #715.


`0.13.0`_ (2021-10-20)
======================

Added
-----

* Allow 16-bit UUID string arguments to ``get_service()`` and ``get_characteristic()``.
* Added ``register_uuids()`` to augment the uuid-to-description mapping.
* Added support for Python 3.10.
* Added ``force_indicate`` keyword argument for WinRT backend client's ``start_notify`` method. Fixes #526.
* Added python-for-android backend.

Changed
-------

* Changed from ``winrt`` dependency to ``bleak-winrt``.
* Improved error when connecting to device fails in WinRT backend. Fixes #647.
* Changed examples to use ``asyncio.run()``.
* Changed the default notify method for the WinRT backend from ``Indicate`` to ``Notify``.
* Refactored GATT error handling in WinRT backend.
* Changed Windows Bluetooth packet capture instructions. Fixes #653.
* Replaced usage of deprecated ``@abc.abstractproperty``.
* Use ``asyncio.get_running_loop()`` instead of ``asyncio.get_event_loop()``.
* Changed "service is already present" exception to logged error in BlueZ backend. Merged #622.

Removed
-------

* Removed ``dotnet`` backend.
* Dropped support for Python 3.6.
* Removed ``use_cached`` kwarg from ``BleakClient`` ``connect()`` and ``get_services()`` methods. Fixes #646.

Fixed
-----

* Fixed unused timeout in the implementation of BleakScanner's ``find_device_by_address()`` function.
* Fixed BleakClient ignoring the ``adapter`` kwarg. Fixes #607.
* Fixed writing descriptors in WinRT backend. Fixes #615.
* Fixed race on disconnect and cleanup of BlueZ matches when device disconnects early. Fixes #603.
* Fixed memory leaks on Windows.
* Fixed protocol error code descriptions on WinRT backend. Fixes #532.
* Fixed race condition hitting assentation in BlueZ ``disconnect()`` method. Fixes #641.
* Fixed enumerating services on a device with HID service on WinRT backend. Fixes #599.
* Fixed subprocess running to check BlueZ version each time a client is created. Fixes #602.
* Fixed exception when discovering services after reconnecting in CoreBluetooth backend.


`0.12.1`_ (2021-07-07)
======================

Changed
-------

* Changed minimum ``winrt`` package version to 1.0.21033.1. Fixes #589.

Fixed
-----

* Fixed unawaited future when writing without response on CoreBluetooth backend.
  Fixes #586.


`0.12.0`_ (2021-06-19)
======================

Added
-----

* Added ``mtu_size`` property for clients.
* Added WinRT backend.
* Added ``BleakScanner.discovered_devices`` property.
* Added an event to await when stopping scanners in WinRT and pythonnet backends. Fixes #556.
* Added ``BleakScanner.find_device_by_filter`` static method.
* Added ``scanner_byname.py`` example.
* Added optional command line argument to specify device to all applicable examples.

Changed
-------

* Added ``Programming Language :: Python :: 3.9`` classifier in ``setup.py``.
* Deprecated ``BleakScanner.get_discovered_devices()`` async method.
* Added capability to handle async functions as detection callbacks in ``BleakScanner``.
* Added error description in addition to error name when ``BleakDBusError`` is converted to string.
* Change typing of data parameter in write methods to ``Union[bytes, bytearray, memoryview]``.
* Improved type hints in CoreBluetooth backend.
* Use delegate callbacks for ``get_rssi()`` on CoreBluetooth backend.
* Use ``@objc.python_method`` where possible in ``PeripheralDelegate`` class.
* Using ObjC key-value observer to wait for ``BleakScanner.start()`` and ``stop()``
  in CoreBluetooth backend.

Fixed
-----

* Fixed ``KeyError`` when trying to connect to ``BLEDevice`` from advertising
  data callback on macOS. Fixes #448.
* Handling of undetected devices in ``connect_by_bledevice.py`` example. Fixes #487.
* Added ``Optional`` typehint for ``BleakScanner.find_device_by_address``.
* Fixed ``linux_autodoc_mock_import`` in ``docs/conf.py``.
* Minor fix for disconnection event handling in BlueZ backend. Fixes #491.
* Corrections for the Philips Hue lamp example. Merged #505.
* Fixed ``BleakClientBlueZDBus.pair()`` method always returning ``True``. Fixes #503.
* Fixed waiting for notification start/stop to complete in CoreBluetooth backend.
* Fixed write without response on BlueZ < 5.51.
* Fixed error propagation for CoreBluetooth events.
* Fixed failed import on CI server when BlueZ is not installed.
* Fixed notification ``value`` should be ``bytearray`` on CoreBluetooth. Fixes #560.
* Fixed crash when cancelling connection when Python runtime shuts down on
  CoreBluetooth backend. Fixes #538.
* Fixed connecting to multiple devices using a single ``BleakScanner`` on
  CoreBluetooth backend.
* Fixed deadlock in CoreBluetooth backend when device disconnects while
  callbacks are pending. Fixes #535.
* Fixed deadlock when using more than one service, characteristic or descriptor
  with the same UUID on CoreBluetooth backend.
* Fixed exception raised when calling ``BleakScanner.stop()`` when already
  stopped in CoreBluetooth backend.


`0.11.0`_ (2021-03-17)
======================

Added
-----

* Updated ``dotnet.client.BleakClientDotNet`` connect method docstring.
* Added ``AdvertisementServiceData`` in BLEDevice in macOS devices
* Protection levels (encryption) in Windows backend pairing. Solves #405.
* Philips Hue lamp example script. Relates to #405.
* Keyword arguments to ``get_services`` method on ``BleakClient``.
* Keyword argument ``use_cached`` on .NET backend, to enable uncached reading
  of services, characteristics and descriptors in Windows.
* Documentation on troubleshooting OS level caches for services.
* New example added: Async callbacks with a queue and external consumer
* ``handle`` property on ``BleakGATTService`` objects
* ``service_handle`` property on ``BleakGATTCharacteristic`` objects
* Added more specific type hints for ``BleakGATTServiceCollection`` properties.
* Added ``asyncio`` task to disconnect devices on event loop crash in BlueZ backend.
* Added filtering on advertisement data callbacks on BlueZ backend so that
  callbacks only occur when advertising data changes like on macOS backend.
* Added fallback to try ``org.bluez.Adapter1.ConnectDevice`` when trying to connect
  a device in BlueZ backend.
* Added UART service example.

Fixed
-----

* Fixed wrong OS write method called in ``write_gatt_descriptor()`` in Windows
  backend.  Merged #403.
* Fixed ``BaseBleakClient.services_resolved`` not reset on disconnect on BlueZ
  backend. Merged #401.
* Fixed RSSI missing in discovered devices on macOS backend. Merged #400.
* Fixed scan result shows 'Unknown' name of the ``BLEDevice``. Fixes #371.
* Fixed a broken check for the correct adapter in ``BleakClientBlueZDBus``.
* Fixed #445 and #362 for Windows.

Changed
-------

* Using handles to identify the services. Added `handle` abstract property to `BleakGATTService`
  and storing the services by handle instead of UUID.
* Changed ``BleakScanner.set_scanning_filter()`` from async method to normal method.
* Changed BlueZ backend to use ``dbus-next`` instead of ``txdbus``.
* Changed ``BleakClient.is_connected`` from async method to property.
* Consolidated D-Bus signal debug messages in BlueZ backend.

Removed
-------

* Removed all ``__str__`` methods from backend service, characteristic and descriptor implementations
  in favour of those in the abstract base classes.



`0.10.0`_ (2020-12-11)
======================

Added
-----

* Added ``AdvertisementData`` class used with detection callbacks across all
  supported platforms. Merged #334.
* Added ``BleakError`` raised during import on unsupported platforms.
* Added ``rssi`` parameter to ``BLEDevice`` constructor.
* Added ``detection_callback`` kwarg to ``BleakScanner`` constructor.

Changed
-------

* Updated minimum PyObjC version to 7.0.1.
* Consolidated implementation of ``BleakScanner.register_detection_callback()``.
  All platforms now take callback with ``BLEDevice`` and ``AdvertisementData``
  arguments.
* Consolidated ``BleakScanner.find_device_by_address()`` implementations.
* Renamed "device" kwarg to "adapter" in BleakClient and BleakScanner. Fixes
  #381.

Fixed
-----

* Fixed use of bare exceptions.
* Fixed ``BleakClientBlueZDBus.start_notify()`` misses initial notifications with
  fast Bluetooth devices. Fixed #374.
* Fix event callbacks on Windows not running in asyncio event loop thread.
* Fixed ``BleakScanner.discover()`` on older versions of macOS. Fixes #331.
* Fixed disconnect callback on BlueZ backend.
* Fixed calling ``BleakClient.is_connected()`` on Mac before connection.
* Fixed kwargs ignored in ``BleakScanner.find_device_by_address()`` in BlueZ backend.
  Fixes #360.

Removed
-------

* Removed duplicate definition of ``BLEDevice`` in BlueZ backend.
* Removed unused imports.
* Removed separate implementation of global ``discover`` method.


`0.9.1`_ (2020-10-22)
=====================

Added
-----

* Added new attribute ``_device_info`` on ``BleakClientBlueZDBus``. Merges #347.
* Added Pull Request Template.

Changed
-------

* Updated instructions on how to contribute, file issues and make PRs.
* Updated ``AUTHORS.rst`` file with development team.

Fixed
-----

* Fix well-known services not converted to UUIDs in ``BLEDevice.metadata`` in
  CoreBluetooth backend. Fixes #342.
* Fix advertising data replaced instead of merged in scanner in CoreBluetooth
  backend. Merged #343.
* Fix CBCentralManager not properly waited for during initialization in some
  cases.
* Fix AttributeError in CoreBluetooth when using BLEDeviceCoreBluetooth object.


`0.9.0`_ (2020-10-20)
=====================

Added
-----

* Timeout for BlueZ backend connect call to avoid potential infinite hanging. Merged #306.
* Added Interfaces API docs again.
* Troubleshooting documentation.
* noqa flags added to ``BleakBridge`` imports.
* Adding a timeout on OSX so that the connect cannot hang forever. Merge #336.

Changed
-------

* ``BleakCharacteristic.description()`` on .NET now returns the same value as
  other platforms.
* Changed all adding and removal of .NET event handler from ``+=``/``-=`` syntax to
  calling ``add_`` and ``remove_`` methods instead. This allows for proper
  removal of event handlers in .NET backend.
* All code dependence on the ``BleakBridge`` is now removed. It is only imported to
  allow for access to UWP namespaces.
* Removing internal method ``_start_notify`` in the .NET backend.
* ``GattSession`` object now manages lifetime of .NET ``BleakClient`` connection.
* ``BleakClient`` in .NET backend will reuse previous device information when
  reconnecting so that it doesn't have to scan/discover again.


Fixed
-----

* UUID property bug fixed in BlueZ backend. Merged #307.
* Fix for broken RTD documentation.
* Fix UUID string arguments should not be case sensitive.
* Fix ``BleakGATTService.get_characteristic()`` method overridden with ``NotImplementedError``
  in BlueZ backend.
* Fix ``AttributeError`` when trying to connect using CoreBluetooth backend. Merged #323.
* Fix disconnect callback called multiple times in .NET backend. Fixes #312.
* Fix ``BleakClient.disconnect()`` method failing when called multiple times in
  .NET backend. Fixes #313.
* Fix ``BleakClient.disconnect()`` method failing when called multiple times in
  Core Bluetooth backend. Merge #333.
* Catch RemoteError in ``is_connected`` in BlueZ backend. Fixes #310,
* Prevent overwriting address in constructor of ``BleakClient`` in BlueZ backend. Merge #311.
* Fix nordic uart UUID. Merge #339.

`0.8.0`_ (2020-09-22)
=====================

Added
-----

* Implemented ``set_disconnected_callback`` in the .NET backend ``BleakClient`` implementation.
* Added ``find_device_by_address`` method to the ``BleakScanner`` interface, for stopping scanning
  when a desired address is found.
* Implemented ``find_device_by_address`` in the .NET backend ``BleakScanner`` implementation and
  switched its ``BleakClient`` implementation to use that method in ``connect``.
* Implemented ``find_device_by_address`` in the BlueZ backend ``BleakScanner`` implementation and
  switched its ``BleakClient`` implementation to use that method in ``connect``.
* Implemented ``find_device_by_address`` in the Core Bluetooth backend ``BleakScanner`` implementation
  and switched its ``BleakClient`` implementation to use that method in ``connect``.
* Added text representations of Protocol Errors that are visible in the .NET backend. Added these texts to errors raised.
* Added pairing method in ``BleakClient`` interface.
* Implemented pairing method in .NET backend.
* Implemented pairing method in the BlueZ backend.
* Added stumps and ``NotImplementedError`` on pairing in macOS backend.
* Added the possibility to connect using ``BLEDevice`` instead of a string address. This
  allows for skipping the discovery call when connecting.

Removed
-------

* Support for Python 3.5.

Changed
-------

* **BREAKING CHANGE** All notifications now have the characteristic's integer **handle** instead of its UUID as a
  string as the first argument ``sender`` sent to notification callbacks. This provides the uniqueness of
  sender in notifications as well.
* Renamed ``BleakClient`` argument ``address`` to ``address_or_ble_device``.
* Version 0.5.0 of BleakUWPBridge, with some modified methods and implementing ``IDisposable``.
* Merged #224. All storing and passing of event loops in bleak is removed.
* Removed Objective C delegate compliance checks. Merged #253.
* Made context managers for .NET ``DataReader`` and ``DataWriter``.

Fixed
-----

* .NET backend loop handling bug entered by #224 fixed.
* Removed default ``DEBUG`` level set to bleak logger. Fixes #251.
* More coherency in logger uses over all backends. Fixes #258
* Attempted fix of #255 and #133: cleanups, disposing of objects and creating new ``BleakBridge`` instances each disconnect.
* Fixed some type hints and docstrings.
* Modified the ``connected_peripheral_delegate`` handling in macOS backend to fix #213 and #116.
* Merged #270, fixing a critical bug in ``get_services`` method in Core Bluetooth backend.
* Improved handling of disconnections and ``is_connected`` in BlueZ backend to fix #259.
* Fix for ``set_disconnected_callback`` on Core Bluetooth. Fixes #276.
* Safer `Core Bluetooth` presence check. Merged #280.

`0.7.1`_ (2020-07-02)
=====================

Changed
-------

* Improved, more explanatory error on BlueZ backend when ``BleakClient`` cannot find the desired device when trying to connect. (#238)
* Better-than-nothing documentation about scanning filters added (#230).
* Ran black on code which was forgotten in 0.7.0. Large diffs due to that.
* Re-adding Python 3.8 CI "tests" on Windows again.

Fixed
-----

* Fix when characteristic updates value faster than asyncio schedule (#240 & #241)
* Incorrect ``MANIFEST.in`` corrected. (#244)


`0.7.0`_ (2020-06-30)
=====================

Added
-----

* Better feedback of communication errors to user in .NET backend and implementing error details proposed in #174.
* Two devices example file to use for e.g. debugging.
* Detection/discovery callbacks in Core Bluetooth backend ``Scanner`` implemented.
* Characteristic handle printout in ``service_explorer.py``.
* Added scanning filters to .NET backend's ``discover`` method.

Changed
-------

* Replace ``NSRunLoop`` with dispatch queue in Core Bluetooth backend. This causes callbacks to be dispatched on a
  background thread instead of on the main dispatch queue on the main thread. ``call_soon_threadsafe()`` is used to synchronize the events
  with the event loop where the central manager was created. Fixes #111.
* The Central Manager is no longer global in the Core Bluetooth backend. A new one is created for each
  ``BleakClient`` and ``BleakScanner``. Fixes #206 and #105.
* Merged #167 and reworked characteristics handling in Bleak. Implemented in all backends;
  bleak now uses the characteristics' handle to identify and keep track of them.
  Fixes #139 and #159 and allows connection for devices with multiple instances
  of the same characteristic UUIDs.
* In ``requirements.txt`` and ``Pipfile``, the requirement on ``pythonnet``
  was bumped to version 2.5.1, which seems to solve issues described in #217 and #225.
* Renamed ``HISTORY.rst`` to ``CHANGELOG.rst`` and adopted
  the `Keep a Changelog <https://keepachangelog.com/en/1.0.0/>`_ format.
* Python 3.5 support from macOS is officially removed since pyobjc>6 requires 3.6+
* Pin ``pyobjc`` dependencies to use at least version 6.2. (PR #194)
* Pin development requirement on `bump2version` to version 1.0.0
* Added ``.pyup.yml`` for Pyup
* Using CBManagerState constants from pyobj instead of integers.

Removed
-------

* Removed documentation note about not using new event loops in Linux. This was fixed by #143.
* ``_central_manager_delegate_ready`` was removed in macOS backend.
* Removed the ``bleak.backends.bluez.utils.get_gatt_service_path`` method. It is not used by
  bleak and possibly generates errors.

Fixed
-----

* Improved handling of the txdbus connection to avoid hanging of disconnection
  clients in BlueZ backend. Fixes #216, #219 & #221.
* #150 hints at the device path not being possible to create as is done in the `get_device_object_path` method.
  Now, we try to get it from BlueZ first. Otherwise, use the old fallback.
* Minor documentation errors corrected.
* ``CBManagerStatePoweredOn`` is now properly handled in Core Bluetooth.
* Device enumeration in ``discover``and ``Scanner`` corrected. Fixes #211
* Updated documentation about scanning filters.
* Added workaround for ``isScanning`` attribute added in macOS 10.13. Fixes #234.

`0.6.4`_ (2020-05-20)
=====================

Fixed
-----

* Fix for bumpversion usage

`0.6.3`_ (2020-05-20)
=====================

Added
-----

* Building and releasing from Github Actions

Removed
-------

* Building and releasing on Azure Pipelines

`0.6.2`_ (2020-05-15)
=====================

Added
-----

* Added ``disconnection_callback`` functionality for Core Bluetooth (#184 & #186)
* Added ``requirements.txt``

Fixed
-----

* Better cleanup of Bluez notifications (#154)
* Fix for ``read_gatt_char`` in Core Bluetooth (#177)
* Fix for ``is_disconnected`` in Core Bluetooth (#187 & #185)
* Documentation fixes

`0.6.1`_ (2020-03-09)
=====================

Fixed
-----

* Including #156, lost notifications on macOS backend, which was accidentally missed on previous release.

`0.6.0`_ (2020-03-09)
=====================

* New Scanner object to allow for async device scanning.
* Updated ``txdbus`` requirement to version 1.1.1 (Merged #122)
* Implemented ``write_gatt_descriptor`` for Bluez backend.
* Large change in Bluez backend handling of Twisted reactors. Fixes #143
* Modified ``set_disconnected_callback`` to actually call the callback as a callback. Fixes #108.
* Added another required parameter to disconnect callbacks.
* Added Discovery filter option in BlueZ backend (Merged #124)
* Merge #138: comments about Bluez version check.
* Improved scanning data for macOS backend. Merge #126.
* Merges #141, a critical fix for macOS.
* Fix for #114, write with response on macOS.
* Fix for #87, DIctionary changes size on .NET backend.
* Fix for #127, uuid or str on macOS.
* Handles str/uuid for characteristics better.
* Merge #148, Run .NET backend notifications on event loop instead of main loop.
* Merge #146, adapt characteristic write log to account for WriteWithoutResponse on macOS.
* Fix for #145, Error in cleanup on Bluez backend.
* Fix for #151, only subscribe to BlueZ messages on DBus. Merge #152.
* Fix for #142, Merge #144, Improved scanning for macOS backend.
* Fix for #155, Merge #156, lost notifications on macOS backend.
* Improved type hints
* Improved error handling for .NET backend.
* Documentation fixes.


0.5.1 (2019-10-09)
==================

* Active Scanning on Windows, #99 potentially solving #95
* Longer timeout in service discovery on BlueZ
* Added ``timeout`` to constructors and connect methods
* Fix for ``get_services`` on macOS. Relates to #101
* Fixes for disconnect callback on BlueZ, #86 and #83
* Fixed reading of device name in BlueZ. It is not readable as regular characteristic. #104
* Removed logger feedback in BlueZ discovery method.
* More verbose exceptions on macOS, #117 and #107

0.5.0 (2019-08-02)
==================

* macOS support added (thanks to @kevincar)
* Merged #90 which fixed #89: Leaking callbacks in BlueZ
* Merged #92 which fixed #91, Prevent leaking of DBus connections on discovery
* Merged #96: Regex patterns
* Merged #86 which fixed #83 and #82
* Recovered old .NET discovery method to try for #95
* Merged #80: macOS development

0.4.3 (2019-06-30)
==================

* Fix for #76
* Fix for #69
* Fix for #74
* Fix for #68
* Fix for #70
* Merged #66

0.4.2 (2019-05-17)
==================

* Fix for missed part of PR #61.

0.4.1 (2019-05-17)
==================

* Merging of PR #61, improvements and fixes for multiple issues for BlueZ backend
* Implementation of issue #57
* Fixing issue #59
* Documentation fixes.

0.4.0 (2019-04-10)
==================

* Transferred code from the BleakUWPBridge C# support project to pythonnet code
* Fixed BlueZ >= 5.48 issues regarding Battery Service
* Fix for issue #55

0.3.0 (2019-03-18)
==================

* Fix for issue #53: Windows and Python 3.7 error
* Azure Pipelines used for CI

0.2.4 (2018-11-30)
==================

* Fix for issue #52: Timing issue getting characteristics
* Additional fix for issue #51.
* Bugfix for string method for BLEDevice.

0.2.3 (2018-11-28)
==================

* Fix for issue #51: ``dpkg-query not found on all Linux systems``

0.2.2 (2018-11-08)
==================

* Made it compliant with Python 3.5 by removing f-strings

0.2.1 (2018-06-28)
==================

* Improved logging on .NET discover method
* Some type annotation fixes in .NET code

0.2.0 (2018-04-26)
==================

* Project added to Github
* First version on PyPI.
* Working Linux (BlueZ DBus API) backend.
* Working Windows (UWP Bluetooth API) backend.

0.1.0 (2017-10-23)
==================

* Bleak created.


.. _Unreleased: https://github.com/hbldh/bleak/compare/v0.20.2...develop
.. _0.20.2: https://github.com/hbldh/bleak/compare/v0.20.1...v0.20.2
.. _0.20.1: https://github.com/hbldh/bleak/compare/v0.20.0...v0.20.1
.. _0.20.0: https://github.com/hbldh/bleak/compare/v0.19.5...v0.20.0
.. _0.19.5: https://github.com/hbldh/bleak/compare/v0.19.4...v0.19.5
.. _0.19.4: https://github.com/hbldh/bleak/compare/v0.19.3...v0.19.4
.. _0.19.3: https://github.com/hbldh/bleak/compare/v0.19.2...v0.19.3
.. _0.19.2: https://github.com/hbldh/bleak/compare/v0.19.1...v0.19.2
.. _0.19.1: https://github.com/hbldh/bleak/compare/v0.19.0...v0.19.1
.. _0.19.0: https://github.com/hbldh/bleak/compare/v0.18.1...v0.19.0
.. _0.18.1: https://github.com/hbldh/bleak/compare/v0.18.0...v0.18.1
.. _0.18.0: https://github.com/hbldh/bleak/compare/v0.17.0...v0.18.0
.. _0.17.0: https://github.com/hbldh/bleak/compare/v0.16.0...v0.17.0
.. _0.16.0: https://github.com/hbldh/bleak/compare/v0.15.1...v0.16.0
.. _0.15.1: https://github.com/hbldh/bleak/compare/v0.15.0...v0.15.1
.. _0.15.0: https://github.com/hbldh/bleak/compare/v0.14.3...v0.15.0
.. _0.14.3: https://github.com/hbldh/bleak/compare/v0.14.2...v0.14.3
.. _0.14.2: https://github.com/hbldh/bleak/compare/v0.14.1...v0.14.2
.. _0.14.1: https://github.com/hbldh/bleak/compare/v0.14.0...v0.14.1
.. _0.14.0: https://github.com/hbldh/bleak/compare/v0.13.0...v0.14.0
.. _0.13.0: https://github.com/hbldh/bleak/compare/v0.12.1...v0.13.0
.. _0.12.1: https://github.com/hbldh/bleak/compare/v0.12.0...v0.12.1
.. _0.12.0: https://github.com/hbldh/bleak/compare/v0.11.0...v0.12.0
.. _0.11.0: https://github.com/hbldh/bleak/compare/v0.10.0...v0.11.0
.. _0.10.0: https://github.com/hbldh/bleak/compare/v0.9.1...v0.10.0
.. _0.9.1: https://github.com/hbldh/bleak/compare/v0.9.0...v0.9.1
.. _0.9.0: https://github.com/hbldh/bleak/compare/v0.8.0...v0.9.0
.. _0.8.0: https://github.com/hbldh/bleak/compare/v0.7.1...v0.8.0
.. _0.7.1: https://github.com/hbldh/bleak/compare/v0.7.0...v0.7.1
.. _0.7.0: https://github.com/hbldh/bleak/compare/v0.6.4...v0.7.0
.. _0.6.4: https://github.com/hbldh/bleak/compare/v0.6.4...v0.6.3
.. _0.6.3: https://github.com/hbldh/bleak/compare/v0.6.3...v0.6.2
.. _0.6.2: https://github.com/hbldh/bleak/compare/v0.6.2...v0.6.1
.. _0.6.1: https://github.com/hbldh/bleak/compare/v0.6.1...v0.6.0
.. _0.6.0: https://github.com/hbldh/bleak/compare/v0.6.0...v0.5.1

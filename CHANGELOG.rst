=========
Changelog
=========

All notable changes to this project will be documented in this file.

The format is based on `Keep a Changelog <https://keepachangelog.com/en/1.0.0/>`_,
and this project adheres to `Semantic Versioning <https://semver.org/spec/v2.0.0.html>`_.


`0.7.0`_ (2020-06-30)
---------------------

Added
~~~~~

* Better feedback of communication errors to user in .NET backend and implementing error details proposed in #174.
* Two devices example file to use for e.g. debugging.
* Detection/discovery callbacks in Core Bluetooth backend ``Scanner`` implemented.
* Characteristic handle printout in ``service_explorer.py``.
* Added scanning filters to .NET backend's ``discover`` method.

Changed
~~~~~~~

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
~~~~~~~

* Removed documentation note about not using new event loops in Linux. This was fixed by #143.
* ``_central_manager_delegate_ready`` was removed in macOS backend.
* Removed the ``bleak.backends.bluez.utils.get_gatt_service_path`` method. It is not used by
  bleak and possibly generates errors.

Fixed
~~~~~

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
---------------------

Fixed
~~~~~

* Fix for bumpversion usage

`0.6.3`_ (2020-05-20)
---------------------

Added
~~~~~

* Building and releasing from Github Actions

Removed
~~~~~~~

* Building and releasing on Azure Pipelines

`0.6.2`_ (2020-05-15)
---------------------

Added
~~~~~
* Added ``disconnection_callback`` functionality for Core Bluetooth (#184 & #186)
* Added ``requirements.txt``

Fixed
~~~~~
* Better cleanup of Bluez notifications (#154)
* Fix for ``read_gatt_char`` in Core Bluetooth (#177)
* Fix for ``is_disconnected`` in Core Bluetooth (#187 & #185)
* Documentation fixes

`0.6.1`_ (2020-03-09)
---------------------

Fixed
~~~~~

* Including #156, lost notifications on macOS backend, which was accidentally missed on previous release.

`0.6.0`_ (2020-03-09)
---------------------

* New Scanner object to allow for async device scanning.
* Updated ``txdbus`` requirement to version 1.1.1 (Merged #122)
* Implemented ``write_gatt_descriptor`` for Bluez backend.
* Large change in Bluez backend handling of Twisted reactors. Fixes #143
* Modified ``set_disconnect_callback`` to actually call the callback as a callback. Fixes #108.
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
------------------

* Active Scanning on Windows, #99 potentially solving #95
* Longer timeout in service discovery on BlueZ
* Added ``timeout`` to constructors and connect methods
* Fix for ``get_services`` on macOS. Relates to #101
* Fixes for disconnect callback on BlueZ, #86 and #83
* Fixed reading of device name in BlueZ. It is not readable as regular characteristic. #104
* Removed logger feedback in BlueZ discovery method.
* More verbose exceptions on macOS, #117 and #107

0.5.0 (2019-08-02)
------------------

* macOS support added (thanks to @kevincar)
* Merged #90 which fixed #89: Leaking callbacks in BlueZ
* Merged #92 which fixed #91, Prevent leaking of DBus connections on discovery
* Merged #96: Regex patterns
* Merged #86 which fixed #83 and #82
* Recovered old .NET discovery method to try for #95
* Merged #80: macOS development

0.4.3 (2019-06-30)
------------------

* Fix for #76
* Fix for #69
* Fix for #74
* Fix for #68
* Fix for #70
* Merged #66

0.4.2 (2019-05-17)
------------------

* Fix for missed part of PR #61.

0.4.1 (2019-05-17)
------------------

* Merging of PR #61, improvements and fixes for multiple issues for BlueZ backend
* Implementation of issue #57
* Fixing issue #59
* Documentation fixes.

0.4.0 (2019-04-10)
------------------

* Transferred code from the BleakUWPBridge C# support project to pythonnet code
* Fixed BlueZ >= 5.48 issues regarding Battery Service
* Fix for issue #55

0.3.0 (2019-03-18)
------------------

* Fix for issue #53: Windows and Python 3.7 error
* Azure Pipelines used for CI

0.2.4 (2018-11-30)
------------------

* Fix for issue #52: Timing issue getting characteristics
* Additional fix for issue #51.
* Bugfix for string method for BLEDevice.

0.2.3 (2018-11-28)
------------------

* Fix for issue #51: ``dpkg-query not found on all Linux systems``

0.2.2 (2018-11-08)
------------------

* Made it compliant with Python 3.5 by removing f-strings

0.2.1 (2018-06-28)
------------------

* Improved logging on .NET discover method
* Some type annotation fixes in .NET code

0.2.0 (2018-04-26)
------------------

* Project added to Github
* First version on PyPI.
* Working Linux (BlueZ DBus API) backend.
* Working Windows (UWP Bluetooth API) backend.

0.1.0 (2017-10-23)
------------------

* Bleak created.


.. _Unreleased: https://github.com/hbldh/bleak/compare/v0.7.0...develop
.. _0.7.0: https://github.com/hbldh/bleak/compare/v0.7.0...v0.6.4
.. _0.6.4: https://github.com/hbldh/bleak/compare/v0.6.3...v0.6.4
.. _0.6.3: https://github.com/hbldh/bleak/compare/v0.6.2...v0.6.3
.. _0.6.2: https://github.com/hbldh/bleak/compare/v0.6.1...v0.6.2
.. _0.6.1: https://github.com/hbldh/bleak/compare/v0.6.0...v0.6.1
.. _0.6.0: https://github.com/hbldh/bleak/compare/v0.5.1...v0.6.0

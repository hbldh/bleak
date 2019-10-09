=======
History
=======

0.5.1 (2019-10-09)
------------------

* Active Scanning on Windows, #99 potentially solving #95
* Longer timeout in service discovery on BlueZ
* Added `timeout` to constructors and connect methods
* Fix for `get_services` on macOS. Relates to #101
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

=======
History
=======


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

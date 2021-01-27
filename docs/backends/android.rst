Android backend
===============

Quick-start: see the `example README <../../examples/kivy/README>`_.  Buildozer
will compile an app and upload it to a device.

There are a handful of ways to run Python on Android.  Presently some code has
been written for the `Python-for-Android <https://python-for-android.readthedocs.io/>`_
build tool, and the code has only been tested using the `Kivy Framework <https://kivy.org/>`_.
The Kivy framework provides a way to make graphical applications using
bluetooth that run on both android and desktop.

An alternative framework is `BeeWare <https://beeware.org>`_.  An implementation
for BeeWare would likely be very similar to Python-for-Android, if anybody is
interested in contributing one.  As of 2020, the major task to tackle is making
a custom template to embed Java subclasses of the Bluetooth Android interfaces,
for forwarding callbacks.

The Python-for-Android backend classes are found in the
``bleak.backends.p4android`` package and are automatically selected when
building with python-for-android or `Buildozer <https://buildozer.readthedocs.io/>`_,
Kivy's automated build tool.

Considerations on Android
-------------------------

For one thing, the python-for-android backend has not been fully tested.
Please run applications with ``adb logcat`` or ``buildozer android logcat`` and
file issues that include the output, so that any compatibility concerns with
devices the developer did not own can be eventually addressed.  This backend
was originally authored by @xloem for a project that has mostly wrapped up now,
so it would be good to tag him in the issues.

When fixing issues, often the Android documentation is lacking, and other
resources may need to be consulted to find information on various device
quirks, such as community developer forums.

Sometimes device drivers will give off new, undocumented error codes.
There is a developing list of these at ``bleak.backends.p4android.defs.GATT_STATUS_NAMES``.
Please add to the list if you find new status codes, which is indicated by a
number being reported instead of a name.

Additionally a few small features are missing.  Please file an issue if you
need a missing feature, and ideally contribute code, so that soon they will all
be implemented.

Two missing features include scanning filters and indications (notifications
without replies).

Additionally reading from a characteristic has not been tested at all, as xloem's
test device did not provide for this.

On Android, Bluetooth needs permissions for access.  These permissions need to
be added to the android application in the buildozer.spec file, and are also
requested from the user at runtime.  This means that enabling bluetooth may not
succeed if the user does not accept permissions.

For an example of building an android bluetooth app, see `the example <../../examples/kivy>`_
and its accompanying `README <../../examples/kivy/README>`_.

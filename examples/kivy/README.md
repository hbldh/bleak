This is a kivy application that lists scanned devices in a desktop window.

It can be run on Android via:

    pip3 install buildozer cython
    # connect phone with USB and enable USB debugging
    buildozer android debug deploy run logcat

Note: changes to `bleak/**` will not be automatically picked up when rebuilding.

This can be worked around by deleting the build directory and rebuilding from
scratch. TODO: find a better way to do this:

    rm -rf .buildozer

An iOS backend has not been implemented yet.

This kivy example can also be run on desktop.

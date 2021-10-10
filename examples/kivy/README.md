This is a kivy application that lists scanned devices in a desktop window.

It can be run on Android via:

    pip3 install buildozer cython
    buildozer android debug
    # connect phone with USB and enable USB debugging
    buildozer android deploy run logcat

Note: changes to `bleak/**` will not be automatically picked up when rebuilding.
Instead the recipe build must be cleaned:

    buildozer android p4a -- clean_recipe_build --local-recipes $(pwd)/../../bleak/backends/p4android/recipes bleak

An iOS backend has not been implemented yet.

This kivy example can also be run on desktop.

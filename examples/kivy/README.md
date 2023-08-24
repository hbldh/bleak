## This is a kivy application that lists scanned devices in a desktop window.

- An iOS backend has not been implemented yet.

- This kivy example can also be run on desktop.

It can be run on Android via:

    pip3 install buildozer cython
    buildozer android debug
    # connect phone with USB and enable USB debugging
    buildozer android deploy run logcat

## To use with local version of bleak source:

Note: changes to `bleak/**` will not be automatically picked up when rebuilding.
Instead the recipe build must be cleaned:

**Update: not tested if bleak source code changes still work via this method.
Since recipe should now automatically install bleak from GitHub release.**


    buildozer android p4a -- clean_recipe_build --local-recipes $(pwd)/../../bleak/backends/p4android/recipes bleak

## To use bleak in your own app:

- Copy the bleak folder under bleak/backends/p4android/recipes into the app recipes folder.
Make sure that 'local_recipes' in buildozer.spec points to the app recipes folder.
The release version set in the recipe will be installed automatically.

- Add 'bleak' and it's dependencies to the requirements in your buildozer.spec file.

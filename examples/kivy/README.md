## This is a kivy application that lists scanned devices in a desktop window

- An iOS backend has not been implemented yet.

- This kivy example can also be run on desktop.

The default target architecture is arm64-v8a.
If you have an older device, change it in the buildozer.spec file (android.archs = arch1, arch2, ..).
Multiple targets are allowed (will significantly increase build time).

It can be run on Android via:

    pip3 install buildozer cython
    buildozer android debug
    # connect phone with USB and enable USB debugging
    buildozer android deploy run logcat

## To use with local version of bleak source:

Local source path can be specified using the P4A_bleak_DIR environment variable:

    P4A_bleak_DIR="path to bleak source" buildozer android debug



Note: changes to `bleak/**` will not be automatically picked up when rebuilding.
Instead the recipe build must be cleaned:

    buildozer android p4a -- clean_recipe_build --local-recipes $(pwd)/../../bleak/backends/p4android/recipes bleak

## To use bleak in your own app:

- Copy the bleak folder under bleak/backends/p4android/recipes into the app recipes folder.
Make sure that 'local_recipes' in buildozer.spec points to the app recipes folder.
The latest version of bleak will be installed automatically.

- Add 'bleak' and it's dependencies to the requirements in your buildozer.spec file.

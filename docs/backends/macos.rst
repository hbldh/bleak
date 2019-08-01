macOS backend
=============

The macOS backend of Bleak is written with pyobjc directives for interfacing
with Foundation and CoreBluetooth APIs. There are some values that pyobjc is
not able to overwrite and thuse the corebleak framework was written to
circumvent these issues. The most noticible difference between the other
backends of bleak and this backend, is that CoreBluetooth doesn't scan for
other devices via MAC address. Instead, UUIDs are utilized that are often
unique between the device that is scanning the the device that is being scanned. 


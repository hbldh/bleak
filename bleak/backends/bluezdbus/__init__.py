import re
import subprocess

from ...exc import BleakError


def check_bluez_version(major: int, minor: int) -> bool:
    """
    Checks the BlueZ version.

    Returns:
        ``True`` if the BlueZ major version is equal to *major* and the minor
        version is greater than or equal to *minor*, otherwise ``False``.
    """
    # lazy-get the version and store it so we only have to run subprocess once
    if not hasattr(check_bluez_version, "version"):
        p = subprocess.Popen(["bluetoothctl", "--version"], stdout=subprocess.PIPE)
        out, _ = p.communicate()
        s = re.search(b"(\\d+).(\\d+)", out.strip(b"'"))

        if not s:
            raise BleakError(f"Could not determine BlueZ version: {out.decode()}")

        setattr(check_bluez_version, "version", tuple(map(int, s.groups())))

    bluez_major, bluez_minor = getattr(check_bluez_version, "version")

    return bluez_major == major and bluez_minor >= minor

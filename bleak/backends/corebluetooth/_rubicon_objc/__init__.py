from .Foundation import NSProcessInfo


def macos_available(major: int, minor: int, patch: int = 0) -> bool:
    version = NSProcessInfo.processInfo.operatingSystemVersion

    current = (version.field_0, version.field_1, version.field_2)
    required = (major, minor, patch)

    return current >= required

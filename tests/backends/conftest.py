import sys

collect_ignore = []

if not sys.platform.startswith("linux"):
    """Ignore bluez tests if module won't exist"""
    collect_ignore.append("bluezdbus")

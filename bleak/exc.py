# -*- coding: utf-8 -*-


class BleakError(Exception):
    """Base Exception for bleak."""

    pass


class BleakDotNetTaskError(BleakError):
    """Wrapped exception that occurred in .NET async Task."""

    pass

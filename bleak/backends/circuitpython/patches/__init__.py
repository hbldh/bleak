"""Monkeypatch absent modules in CircuitPython"""
import sys


def apply_patches():
    if sys.implementation.name == "circuitpython":
        import builtins
        assert builtins
        import asyncio
        assert asyncio

        from . import _fake_enum
        from . import _fake_types
        from . import _fake_typing
        from . import _inspect
        from . import _platform
        from . import _fake_abc
        from . import _fake_collections_abc
        from . import _uuid
        from . import _deprecation_warn
        from ._async_timeout import async_timeout as _async_timeout
        import adafruit_logging as _logging
        import circuitpython_functools as _functools

        if 'builtins' not in sys.modules:
            sys.modules['builtins'] = builtins
        sys.modules["builtins"].DeprecationWarning = _deprecation_warn.DeprecationWarning
        sys.modules["enum"] = _fake_enum
        sys.modules["inspect"] = _inspect
        sys.modules["platform"] = _platform
        sys.modules["uuid"] = _uuid
        sys.modules["types"] = _fake_types
        sys.modules["typing"] = _fake_typing
        sys.modules["typing_extensions"] = _fake_typing
        sys.modules["logging"] = _logging
        sys.modules["abc"] = _fake_abc
        sys.modules["collections.abc"] = _fake_collections_abc
        sys.modules['functools'] = _functools
        sys.modules['asyncio'].timeout = _async_timeout

        print("patched")

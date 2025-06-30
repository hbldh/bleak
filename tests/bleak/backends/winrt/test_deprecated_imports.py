import sys

import pytest

# isort: off

if not sys.platform.startswith("win"):
    pytest.skip("backend only available on windows", allow_module_level=True)


def test_deprecated_WinRTClientArgs_import():
    with pytest.warns(
        DeprecationWarning,
        match="importing WinRTClientArgs from bleak.backends.winrt.client is deprecated, use bleak.args.winrt instead",
    ) as recorder:
        from bleak.backends.winrt.client import (  # noqa: F401
            WinRTClientArgs,  # type: ignore[unused-import]
        )

    assert recorder.list[0].filename == __file__

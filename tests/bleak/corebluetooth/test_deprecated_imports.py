import sys

import pytest

# isort: off

if not sys.platform.startswith("darwin"):
    pytest.skip("backend only available on macOS", allow_module_level=True)


def test_deprecated_CBScannerArgs_import():
    with pytest.warns(
        DeprecationWarning,
        match="importing CBScannerArgs from bleak.backends.corebluetooth.scanner is deprecated, use bleak.args.corebluetooth instead",
    ) as recorder:
        from bleak.backends.corebluetooth.scanner import (  # noqa: F401
            CBScannerArgs,  # type: ignore[unused-import]
        )

    assert recorder.list[0].filename == __file__

import sys

import pytest

# isort: off

if not sys.platform.startswith("linux"):
    pytest.skip("backend only available on Linux", allow_module_level=True)


def test_deprecated_OrPattern_import():
    with pytest.warns(
        DeprecationWarning,
        match="importing OrPattern from bleak.backends.bluezdbus.advertisement_monitor is deprecated",
    ) as recorder:
        from bleak.backends.bluezdbus.advertisement_monitor import (  # noqa: F401
            OrPattern,  # type: ignore[unused-import]
        )

    assert recorder.list[0].filename == __file__


def test_deprecated_OrPatternLike_import():
    with pytest.warns(
        DeprecationWarning,
        match="importing OrPatternLike from bleak.backends.bluezdbus.advertisement_monitor is deprecated",
    ) as recorder:
        from bleak.backends.bluezdbus.advertisement_monitor import (  # noqa: F401
            OrPatternLike,  # type: ignore[unused-import]
        )

    assert recorder.list[0].filename == __file__


def test_deprecated_BlueZDiscoveryFilters_import():
    with pytest.warns(
        DeprecationWarning,
        match="importing BlueZDiscoveryFilters from bleak.backends.bluezdbus.scanner is deprecated",
    ) as recorder:
        from bleak.backends.bluezdbus.scanner import (  # noqa: F401
            BlueZDiscoveryFilters,  # type: ignore[unused-import]
        )
    assert recorder.list[0].filename == __file__


def test_deprecated_BlueZScannerArgs_import():
    with pytest.warns(
        DeprecationWarning,
        match="importing BlueZScannerArgs from bleak.backends.bluezdbus.scanner is deprecated",
    ) as recorder:
        from bleak.backends.bluezdbus.scanner import (  # noqa: F401
            BlueZScannerArgs,  # type: ignore[unused-import]
        )

    assert recorder.list[0].filename == __file__

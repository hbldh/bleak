import sys

import pytest

if sys.platform != "darwin":
    pytest.skip("CoreBluetooth only tests", allow_module_level=True)
    # unreachable, but makes the type checkers happy
    assert False

from unittest.mock import Mock

from CoreBluetooth import (
    CBManagerAuthorizationDenied,
    CBManagerAuthorizationRestricted,
    CBManagerStatePoweredOff,
    CBManagerStateResetting,
    CBManagerStateUnauthorized,
    CBManagerStateUnknown,
    CBManagerStateUnsupported,
)

from bleak import BleakScanner
from bleak.backends.corebluetooth.scanner import BleakScannerCoreBluetooth
from bleak.exc import BleakBluetoothNotAvailableError, BleakBluetoothNotAvailableReason


@pytest.mark.parametrize(
    "state,authorization,expected_msg,expected_reason",
    [
        pytest.param(
            CBManagerStateUnsupported,
            None,
            "unsupported",
            BleakBluetoothNotAvailableReason.NO_BLUETOOTH,
            id="unsupported",
        ),
        pytest.param(
            CBManagerStateUnauthorized,
            CBManagerAuthorizationDenied,
            "denied by the user",
            BleakBluetoothNotAvailableReason.DENIED_BY_USER,
            id="unauthorized_denied",
        ),
        pytest.param(
            CBManagerStateUnauthorized,
            CBManagerAuthorizationRestricted,
            "restricted",
            BleakBluetoothNotAvailableReason.DENIED_BY_SYSTEM,
            id="unauthorized_restricted",
        ),
        pytest.param(
            CBManagerStateUnauthorized,
            999,  # Unknown authorization status
            "not authorized",
            BleakBluetoothNotAvailableReason.DENIED_BY_UNKNOWN,
            id="unauthorized_unknown",
        ),
        pytest.param(
            CBManagerStatePoweredOff,
            None,
            "turned off",
            BleakBluetoothNotAvailableReason.POWERED_OFF,
            id="powered_off",
        ),
        pytest.param(
            CBManagerStateResetting,
            None,
            "Connection to the Bluetooth system service was lost",
            BleakBluetoothNotAvailableReason.UNKNOWN,
            id="resetting",
        ),
        pytest.param(
            CBManagerStateUnknown,
            None,
            "state is unknown",
            BleakBluetoothNotAvailableReason.UNKNOWN,
            id="unknown_state",
        ),
    ],
)
async def test_bluetooth_availability(
    monkeypatch: pytest.MonkeyPatch,
    state: int,
    authorization: int | object,
    expected_msg: str,
    expected_reason: BleakBluetoothNotAvailableReason,
):
    """An Exception is raised, when bluetooth is not available."""

    scanner = BleakScanner()

    # Unfortunately it is not possible to modify the bluetooth state on a macOS pro
    # programmatically. Therefore, we use mocking to emulate various states.
    backend = scanner._backend  # pyright: ignore[reportPrivateUsage]
    assert isinstance(
        backend,
        BleakScannerCoreBluetooth,
    )
    central_manager_delegate = backend._manager  # pyright: ignore[reportPrivateUsage]

    mock_manager = Mock(wraps=central_manager_delegate.central_manager)
    mock_manager.state.return_value = state
    if authorization is not None:
        mock_manager.authorization.return_value = authorization

    monkeypatch.setattr(
        central_manager_delegate,
        "central_manager",
        mock_manager,
    )

    # Starting the scanner should raise the appropriate exception
    with pytest.raises(BleakBluetoothNotAvailableError, match=expected_msg) as exc_info:
        async with scanner:
            pass

    assert exc_info.value.reason == expected_reason

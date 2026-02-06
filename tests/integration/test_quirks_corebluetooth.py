import sys

import pytest

if sys.platform != "darwin":
    pytest.skip("CoreBluetooth only tests", allow_module_level=True)
    # unreachable, but makes the type checkers happy
    assert False

import gc
import weakref
from unittest.mock import Mock

from bumble.device import Device

from bleak import BleakClient, BleakScanner
from bleak.backends.corebluetooth._objc_compat import (
    BLEAK_OBJC_FRAMEWORK_IS_PYOBJC,
    BLEAK_OBJC_FRAMEWORK_IS_RUBICON,
    CBManagerAuthorizationDenied,
    CBManagerAuthorizationRestricted,
    CBManagerStatePoweredOff,
    CBManagerStateResetting,
    CBManagerStateUnauthorized,
    CBManagerStateUnknown,
    CBManagerStateUnsupported,
)
from bleak.backends.corebluetooth.CentralManagerDelegate import CentralManagerDelegate
from bleak.backends.corebluetooth.client import BleakClientCoreBluetooth
from bleak.backends.corebluetooth.PeripheralDelegate import PeripheralDelegate
from bleak.backends.corebluetooth.scanner import BleakScannerCoreBluetooth
from bleak.exc import BleakBluetoothNotAvailableError, BleakBluetoothNotAvailableReason
from tests.integration.conftest import (
    configure_and_power_on_bumble_peripheral,
    find_ble_device,
)


def objc_prop_mock(value: object) -> object:
    if BLEAK_OBJC_FRAMEWORK_IS_PYOBJC:
        return lambda: value
    if BLEAK_OBJC_FRAMEWORK_IS_RUBICON:
        return value


def get_central_manager_delegate(
    scanner: BleakScanner,
) -> CentralManagerDelegate:
    """Get the private CentralManagerDelegate Object from the scanner."""
    backend = scanner._backend  # pyright: ignore[reportPrivateUsage]
    assert isinstance(
        backend,
        BleakScannerCoreBluetooth,
    )
    central_manager_delegate = backend._manager  # pyright: ignore[reportPrivateUsage]
    return central_manager_delegate


def get_peripheral_delegate(
    client: BleakClient,
) -> PeripheralDelegate:
    """Get the private PeripheralDelegate Object from the client."""
    backend = client._backend  # pyright: ignore[reportPrivateUsage]
    assert isinstance(
        backend,
        BleakClientCoreBluetooth,
    )
    peripheral_delegate = backend._delegate  # pyright: ignore[reportPrivateUsage]
    assert peripheral_delegate is not None
    return peripheral_delegate


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
    central_manager_delegate = get_central_manager_delegate(scanner)
    mock_manager = Mock(wraps=central_manager_delegate.central_manager)
    mock_manager.state = objc_prop_mock(state)
    if authorization is not None:
        mock_manager.authorization = objc_prop_mock(authorization)

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


async def test_central_manager_circular_references():
    """No circular references between CentralManagerDelegate and ObjcCentralManagerDelegate."""
    scanner = BleakScanner()

    # Create a weak reference to the CentralManagerDelegate, to verify
    # it gets garbage collected
    central_manager_delegate_ref = weakref.ref(get_central_manager_delegate(scanner))
    assert central_manager_delegate_ref() is not None

    # Delete the scanner and force garbage collection, so that the CentralManagerDelegate
    # can be garbage collected
    del scanner
    gc.collect()

    # The manager should be garbage collected if there are no circular references
    assert central_manager_delegate_ref() is None


async def test_peripheral_circular_references(bumble_peripheral: Device):
    """No circular references between PeripheralDelegate and ObjcPeripheralDelegate."""
    await configure_and_power_on_bumble_peripheral(bumble_peripheral)

    device = await find_ble_device(bumble_peripheral)

    # We need to connect to the device to ensure that the PeripheralDelegate is created
    client = BleakClient(device)
    async with client:
        pass

    # Create a weak reference to the PeripheralDelegate, to verify
    # it gets garbage collected
    peripheral_delegate_ref = weakref.ref(get_peripheral_delegate(client))
    assert peripheral_delegate_ref() is not None

    # Delete the client and force garbage collection, so that the PeripheralDelegate
    # can be garbage collected
    del client
    gc.collect()

    # The delegate should be garbage collected if there are no circular references
    assert peripheral_delegate_ref() is None

from pathlib import Path
from typing import AsyncGenerator

import pytest
from bumble import data_types
from bumble.controller import Controller
from bumble.core import AdvertisingData, DataType
from bumble.device import Device, DeviceConfiguration
from bumble.hci import Address
from bumble.transport import open_transport
from bumble.transport.common import Transport

from tests.integration.bluez_controller import open_bluez_bluetooth_controller_link


@pytest.fixture
async def hci_transport(
    request: pytest.FixtureRequest,
    tmp_path: Path,
) -> AsyncGenerator[Transport, None]:
    """Create a bumble HCI Transport."""
    hci_transport_name: str | None = request.config.getoption("--bleak-hci-transport")
    bluez_hci_transport_name: str | None = request.config.getoption(
        "--bleak-bluez-hci-transport"
    )

    if (hci_transport_name is not None) and (bluez_hci_transport_name is not None):
        raise pytest.UsageError(
            "Cannot use --bleak-hci-transport and "
            "--bleak-bluez-hci-transport together"
        )
    elif bluez_hci_transport_name is not None:
        async with open_bluez_bluetooth_controller_link(
            bluez_hci_transport_name
        ) as local_link:
            device_controller = Controller("C-DEVICE", link=local_link)
            yield Transport(device_controller, device_controller)
    elif hci_transport_name is not None:
        async with await open_transport(hci_transport_name) as hci_transport:
            yield hci_transport
    else:
        pytest.skip(
            "No HCI transport provided (use --bleak-hci-transport or --bleak-bluez-hci-transport)"
        )


@pytest.fixture
def bumble_peripheral(hci_transport: Transport) -> Device:
    """
    Create a BLE peripheral device with bumble.
    """
    config = DeviceConfiguration(
        name="Bleak",
        # use random static address to avoid device caching issues, when characteristics change between test runs
        address=Address.generate_static_address(),
        advertising_interval_min=200,
        advertising_interval_max=200,
    )
    return Device.from_config_with_hci(
        config,
        hci_transport.source,
        hci_transport.sink,
    )


def add_default_advertising_data(
    bumble_peripheral: Device,
    additional_adv_data: list[DataType] | None = None,
) -> None:
    """Add default advertising data to bumble peripheral."""
    adv_data: list[DataType] = [
        data_types.Flags(
            AdvertisingData.Flags.LE_GENERAL_DISCOVERABLE_MODE
            | AdvertisingData.Flags.BR_EDR_NOT_SUPPORTED
        ),
        data_types.CompleteLocalName(bumble_peripheral.name),
    ]
    if additional_adv_data:
        adv_data.extend(additional_adv_data)
    bumble_peripheral.advertising_data = bytes(AdvertisingData(adv_data))

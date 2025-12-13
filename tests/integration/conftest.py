from pathlib import Path
from typing import AsyncGenerator

import pytest
from bumble.device import Device, DeviceConfiguration
from bumble.hci import Address
from bumble.transport import open_transport
from bumble.transport.common import Transport


@pytest.fixture(scope="function")
async def hci_transport(
    request: pytest.FixtureRequest,
    tmp_path: Path,
) -> AsyncGenerator[Transport, None]:
    """Create a bumble HCI Transport."""
    hci_transport_name: str | None = request.config.getoption("--hci-transport")

    if not hci_transport_name:
        pytest.skip("No HCI transport provided (use --hci-transport)")
    else:
        async with await open_transport(hci_transport_name) as hci_transport:
            yield hci_transport


def create_bumble_peripheral(hci_transport: Transport) -> Device:
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

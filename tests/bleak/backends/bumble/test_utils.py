from bumble.controller import Controller
from bumble.device import Device
from bumble.hci import Address
from bumble.host import Host

from bleak.backends.bumble import BumbleTransportCfg, TransportScheme, get_link

test_transport = BumbleTransportCfg(TransportScheme.TCP_SERVER, "127.0.0.1:1000")


def get_device(addr: str) -> Device:
    """Initialize and return a bumble BLE device with the specified address."""
    device = Device("", Address(addr))
    device.host = Host()
    device.host.controller = Controller("dev", link=get_link())
    return device

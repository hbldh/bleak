import asyncio
import contextlib
import logging
from typing import AsyncGenerator, cast

from bumble import hci
from bumble.controller import Controller
from bumble.link import LocalLink
from bumble.transport import open_transport

EMPTY_ADDRESS = hci.Address("00:00:00:00:00:00")


def log_output(output: bytes, prefix: str = "") -> None:
    """Log subprocess output line by line."""
    for line in output.decode(errors="ignore").splitlines():
        logging.debug(f"{prefix}{line}")


async def run_bluetoothctl(commands: list[str]) -> tuple[int, str, str]:
    """Run bluetoothctl with the given commands."""
    bt = await asyncio.create_subprocess_exec(
        "bluetoothctl",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    commands_str = "\n".join(commands) + "\n"
    stdout, stderr = await bt.communicate(input=commands_str.encode())

    return (
        bt.returncode or 0,
        stdout.decode(errors="ignore"),
        stderr.decode(errors="ignore"),
    )


async def controller_available(address: hci.Address) -> bool:
    """Check if a Bluetooth controller is available via bluetoothctl show."""
    commands = [f"show {address}", "quit"]
    _, stdout, _ = await run_bluetoothctl(commands)

    if "Manufacturer: 0xffff" in stdout:
        return True
    return False


async def power_on_controller(address: hci.Address) -> None:
    """Power on a Bluetooth controller via bluetoothctl."""
    commands = [f"select {address}", "power on", "quit"]
    returncode, stdout, stderr = await run_bluetoothctl(commands)

    if returncode != 0 or "Failed to power on" in stdout:
        logging.error(f"bluetoothctl failed with return code {returncode}")
        log_output(stdout.encode(), prefix="bluetoothctl stdout: ")
        log_output(stderr.encode(), prefix="bluetoothctl stderr: ")
        raise RuntimeError("Failed to power on controller via bluetoothctl")


async def wait_for_controller_connected(
    bluez_controller: Controller, timeout: float = 5.0
) -> hci.Address:
    """Wait for BlueZ to connect to the controller."""
    while True:
        # When BlueZ connects to the controller, it will change its random address.
        # We can use this as an indication that the controller is connected to BlueZ.
        random_address = cast(hci.Address, bluez_controller.random_address)  # type: ignore
        if random_address != EMPTY_ADDRESS:
            logging.info(
                "bluez changed random address of controller, so the controller is connected to bluez"
            )

            # Check if controller is available, to be sure bluetoothctl can see it
            if await controller_available(random_address):
                logging.info("btattach started and controller is available")
                return random_address

        logging.info("waiting for btattach to start and controller to become available")
        await asyncio.sleep(0.1)


@contextlib.asynccontextmanager
async def open_bluez_bluetooth_controller_link(
    hci_transport_name: str,
) -> AsyncGenerator[LocalLink, None]:
    """
    Open a local link (virtual RF connection) to a bumble Bluetooth
    controller that is connected to BlueZ.
    """
    # Open a HCI transport connected to the OS
    async with await open_transport(hci_transport_name) as hci_transport:
        # Local link to create virtual RF connection between multiple Bluetooth Controllers
        link = LocalLink()

        # Bluetooth controller that BlueZ can connect to.
        # (This will register itself to the link.)
        bluez_controller = Controller(
            "C-BLUEZ",
            host_source=hci_transport.source,
            host_sink=hci_transport.sink,
            link=link,
        )

        # Wait up to 5 seconds for the controller to appear via `bluetoothctl show`
        random_address = await asyncio.wait_for(
            wait_for_controller_connected(bluez_controller), timeout=5.0
        )

        # Ensure controller is powered on
        await power_on_controller(random_address)

        # Yield the local link for use in tests
        yield link

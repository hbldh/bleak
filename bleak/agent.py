import abc
from typing import Optional

from .backends.device import BLEDevice


class BaseBleakAgentCallbacks(abc.ABC):
    @abc.abstractmethod
    async def confirm(self, device: BLEDevice) -> bool:
        """
        Implementers should prompt the user to confirm or reject the pairing
        request.

        Returns:
            ``True`` to accept the pairing request or ``False`` to reject it.
        """

    @abc.abstractmethod
    async def confirm_pin(self, device: BLEDevice, pin: str) -> bool:
        """
        Implementers should display the pin code to the user and prompt the
        user to validate the pin code and confirm or reject the pairing request.

        Args:
            pin: The pin code to be confirmed.

        Returns:
            ``True`` to accept the pairing request or ``False`` to reject it.
        """

    @abc.abstractmethod
    async def display_pin(self, device: BLEDevice, pin: str) -> None:
        """
        Implementers should display the pin code to the user.

        This method should block indefinitely until it canceled (i.e.
        ``await asyncio.Event().wait()``).

        Args:
            pin: The pin code to be confirmed.
        """

    @abc.abstractmethod
    async def request_pin(self, device: BLEDevice) -> Optional[str]:
        """
        Implementers should prompt the user to enter a pin code to accept the
        pairing request or to reject the paring request.

        Returns:
            A string containing the pin code to accept the pairing request or
            ``None`` to reject it.
        """

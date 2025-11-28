import abc

from .backends.device import BLEDevice


class BaseBleakAgentCallbacks(abc.ABC):
    @abc.abstractmethod
    async def request_passkey(self, device: BLEDevice) -> str:
        """
        Implementers should ask the user the passkey displayed on the device.

        Returns:
            Passkey provided by the user
        """

    @abc.abstractmethod
    async def confirm_passkey(self, device: BLEDevice, passkey: str) -> bool:
        """
        Implementers should display the passkey code to the user and prompt the
        user to validate the passkey code and confirm or reject the pairing request.

        Args:
            pin: The passkey to be confirmed.

        Returns:
            ``True`` to accept the pairing request or ``False`` to reject it.
        """

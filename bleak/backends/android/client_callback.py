from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    if sys.platform != "android":
        assert False, "This backend is only available on Android"

import asyncio
import dataclasses
import logging
from typing import TYPE_CHECKING, Any

from android.bluetooth import (
    BluetoothGatt,
    BluetoothGattCallback,
    BluetoothGattCharacteristic,
    BluetoothGattDescriptor,
    BluetoothProfile,
)
from java import Override, jarray, jbyte, jint, jvoid, static_proxy

from bleak.backends._utils import external_thread_callback
from bleak.backends.android.dispatcher import (
    CallbackApi,
    CallbackDispatcher,
    CallbackResult,
    EmptyCallbackResult,
)
from bleak.backends.android.status import GATT_SUCCESS
from bleak.exc import BleakGATTProtocolError

if TYPE_CHECKING:
    # Only for type checking. At runtime this results in an error.
    from bleak.backends.android.client import BleakClientAndroid

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class OnConnectionStateChangeResult(CallbackResult):
    new_state: int


@dataclasses.dataclass(frozen=True)
class OnConnectionStateChangeCallback(CallbackApi[OnConnectionStateChangeResult]):
    pass


@dataclasses.dataclass
class OnMtuChangedResult(CallbackResult):
    mtu: int


@dataclasses.dataclass(frozen=True)
class OnMtuChangedCallback(CallbackApi[OnMtuChangedResult]):
    pass


@dataclasses.dataclass(frozen=True)
class OnServicesDiscoveredCallback(CallbackApi[EmptyCallbackResult]):
    pass


@dataclasses.dataclass
class OnCharacteristicReadResult(CallbackResult):
    value: bytes


@dataclasses.dataclass(frozen=True)
class OnCharacteristicReadCallback(CallbackApi[OnCharacteristicReadResult]):
    handle: int


@dataclasses.dataclass(frozen=True)
class OnCharacteristicWriteCallback(CallbackApi[EmptyCallbackResult]):
    handle: int


@dataclasses.dataclass
class OnDescriptorReadResult(CallbackResult):
    value: bytes


@dataclasses.dataclass(frozen=True)
class OnDescriptorReadCallback(CallbackApi[OnDescriptorReadResult]):
    uuid: str


@dataclasses.dataclass(frozen=True)
class OnDescriptorWriteCallback(CallbackApi[EmptyCallbackResult]):
    uuid: str


class PythonBluetoothGattCallback(static_proxy(BluetoothGattCallback)):  # type: ignore[misc]
    """Callback class for GattClient. PRIVATE."""

    def __init__(self, client: "BleakClientAndroid", loop: asyncio.AbstractEventLoop):
        super(PythonBluetoothGattCallback, self).__init__()
        self.java = self
        self._loop = loop
        self._client = client
        self.dispatcher = CallbackDispatcher(loop)

    @Override(jvoid, [BluetoothGatt, jint, jint])
    @external_thread_callback
    def onConnectionStateChange(self, gatt: BluetoothGatt, status: int, newState: int):
        logger.debug(f"onConnectionStateChange {status=} {newState=}")
        self.dispatcher.result_state_threadsafe(
            BleakGATTProtocolError(int(status)) if status != GATT_SUCCESS else None,
            OnConnectionStateChangeCallback(),
            OnConnectionStateChangeResult(int(newState)),
        )
        disconnected_callback = (
            self._client._disconnected_callback  # pyright: ignore[reportPrivateUsage]
        )
        if (
            newState == BluetoothProfile.STATE_DISCONNECTED
            and disconnected_callback is not None
        ):
            self._loop.call_soon_threadsafe(disconnected_callback)

    @Override(jvoid, [BluetoothGatt, jint, jint])
    @external_thread_callback
    def onMtuChanged(self, gatt: BluetoothGatt, mtu: int, status: int):
        logger.debug(f"onMtuChanged {mtu=} {status=}")
        self.dispatcher.result_state_threadsafe(
            BleakGATTProtocolError(int(status)) if status != GATT_SUCCESS else None,
            OnMtuChangedCallback(),
            OnMtuChangedResult(int(mtu)),
        )

    @Override(jvoid, [BluetoothGatt, jint])
    @external_thread_callback
    def onServicesDiscovered(self, gatt: BluetoothGatt, status: int):
        logger.debug(f"onServicesDiscovered {status=}")
        self.dispatcher.result_state_threadsafe(
            BleakGATTProtocolError(int(status)) if status != GATT_SUCCESS else None,
            OnServicesDiscoveredCallback(),
            EmptyCallbackResult(),
        )

    @Override(  # API level 33 and above
        jvoid,
        [BluetoothGatt, BluetoothGattCharacteristic, jarray(jbyte)],
    )
    @Override(  # API level 32 and below
        jvoid, [BluetoothGatt, BluetoothGattCharacteristic]
    )
    @external_thread_callback
    def onCharacteristicChanged(
        self,
        gatt: BluetoothGatt,
        characteristic: BluetoothGattCharacteristic,
        *args: Any,
    ):
        logger.debug("onCharacteristicChanged")
        handle = characteristic.getInstanceId()
        if len(args) == 0:
            # On API level 32 (Android 12) and below
            value = characteristic.getValue()
        else:
            # On API level 33 (Android 13) and above
            value = args[0]

        conn_objs = self._client._conn_objs  # pyright: ignore[reportPrivateUsage]
        if conn_objs is not None:
            callback = conn_objs.subscriptions.get(handle)
            if callback is None:
                logger.debug("Ignoring notification for unsubscribed handle %s", handle)
                return
            self._loop.call_soon_threadsafe(
                callback,
                bytearray(value),
            )

    @Override(  # API level 33 and above
        jvoid,
        [BluetoothGatt, BluetoothGattCharacteristic, jarray(jbyte), jint],
    )
    @Override(  # API level 32 and below
        jvoid, [BluetoothGatt, BluetoothGattCharacteristic, jint]
    )
    @external_thread_callback
    def onCharacteristicRead(
        self,
        gatt: BluetoothGatt,
        characteristic: BluetoothGattCharacteristic,
        *args: Any,
    ):
        logger.debug("onCharacteristicRead")
        handle = characteristic.getInstanceId()
        status = args[-1]
        if len(args) == 1:
            # On API level 32 (Android 12) and below
            value = characteristic.getValue()
        else:
            # On API level 33 (Android 13) and above
            value = args[0]
        self.dispatcher.result_state_threadsafe(
            BleakGATTProtocolError(int(status)) if status != GATT_SUCCESS else None,
            OnCharacteristicReadCallback(handle),
            OnCharacteristicReadResult(bytes(value)),
        )

    @Override(jvoid, [BluetoothGatt, BluetoothGattCharacteristic, jint])
    @external_thread_callback
    def onCharacteristicWrite(
        self,
        gatt: BluetoothGatt,
        characteristic: BluetoothGattCharacteristic,
        status: int,
    ):
        logger.debug(f"onCharacteristicWrite {status=}")
        handle = characteristic.getInstanceId()
        self.dispatcher.result_state_threadsafe(
            BleakGATTProtocolError(int(status)) if status != GATT_SUCCESS else None,
            OnCharacteristicWriteCallback(handle),
            EmptyCallbackResult(),
        )

    @Override(
        jvoid,
        [BluetoothGatt, BluetoothGattDescriptor, jint, jarray(jbyte)],
    )
    @Override(jvoid, [BluetoothGatt, BluetoothGattDescriptor, jint])
    @external_thread_callback
    def onDescriptorRead(
        self,
        gatt: BluetoothGatt,
        descriptor: BluetoothGattDescriptor,
        status: int,
        *args: Any,
    ):
        logger.debug(f"onDescriptorRead {status=}")
        uuid = str(descriptor.getUuid())
        if len(args) == 0:
            # On API level 32 (Android 12) and below
            value = descriptor.getValue()
        else:
            # On API level 33 (Android 13) and above
            value = args[0]
        self.dispatcher.result_state_threadsafe(
            BleakGATTProtocolError(int(status)) if status != GATT_SUCCESS else None,
            OnDescriptorReadCallback(uuid),
            OnDescriptorReadResult(bytes(value)),
        )

    @Override(jvoid, [BluetoothGatt, BluetoothGattDescriptor, jint])
    @external_thread_callback
    def onDescriptorWrite(
        self,
        gatt: BluetoothGatt,
        descriptor: BluetoothGattDescriptor,
        status: int,
    ):
        logger.debug(f"onDescriptorWrite {status=}")
        uuid = str(descriptor.getUuid())
        self.dispatcher.result_state_threadsafe(
            BleakGATTProtocolError(int(status)) if status != GATT_SUCCESS else None,
            OnDescriptorWriteCallback(uuid),
            EmptyCallbackResult(),
        )

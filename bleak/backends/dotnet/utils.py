# -*- coding: utf-8 -*-
"""
Helper methods for awaiting on .NET Tasks.

Created on 2017-12-05 by hbldh <henrik.blidh@nedomkull.com>
"""

import asyncio

from bleak.exc import BleakDotNetTaskError

# Import of BleakBridge to enable loading of winrt bindings
from BleakBridge import Bridge  # noqa: F401

# Python for .NET CLR imports
from System import Action
from System.Threading.Tasks import Task

from Windows.Foundation import (
    AsyncOperationCompletedHandler,
    IAsyncOperation,
    AsyncStatus,
)
from System import Array, Byte
from Windows.Storage.Streams import DataReader, DataWriter, IBuffer


async def wrap_Task(task):
    """Enables await on .NET Task using asyncio.Event and a lambda callback.

    Args:
        task (System.Threading.Tasks.Task): .NET async task object
        to await upon.

    Returns:
        The results of the the .NET Task.

    """
    loop = asyncio.get_event_loop()
    done = asyncio.Event()
    # Register Action<Task> callback that triggers the above asyncio.Event.
    task.ContinueWith(Action[Task](lambda x: loop.call_soon_threadsafe(done.set)))
    # Wait for callback.
    await done.wait()
    # TODO: Handle IsCancelled.
    if task.IsFaulted:
        # Exception occurred. Wrap it in BleakDotNetTaskError
        # to make it catchable.
        raise BleakDotNetTaskError(task.Exception.ToString())

    return task.Result


async def wrap_IAsyncOperation(op: IAsyncOperation, return_type):
    """Enables await on .NET Task using asyncio.Event and a lambda callback.

    Args:
        op (Windows.Foundation.IAsyncOperation[TResult]): .NET async operation object to await.
        result_type (TResult): The .NET type of the result of the async operation.

    Returns:
        The results of the the .NET Task.

    """
    loop = asyncio.get_event_loop()
    done = asyncio.Event()
    # Register AsyncOperationCompletedHandler callback that triggers the above asyncio.Event.
    op.Completed = AsyncOperationCompletedHandler[return_type](
        lambda x, y: loop.call_soon_threadsafe(done.set)
    )
    # Wait for callback.
    await done.wait()

    if op.Status == AsyncStatus.Completed:
        return op.GetResults()
    elif op.Status == AsyncStatus.Error:
        # Exception occurred. Wrap it in BleakDotNetTaskError
        # to make it catchable.
        raise BleakDotNetTaskError(op.ErrorCode.ToString())
    else:
        # TODO: Handle IsCancelled.
        raise BleakDotNetTaskError("IAsyncOperation Status: {0}".format(op.Status))


class BleakDataReader:
    def __init__(self, buffer_com_object):

        self.reader = None
        self.buffer = IBuffer(buffer_com_object)

    def __enter__(self):
        self.reader = DataReader.FromBuffer(self.buffer)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.reader.DetachBuffer()
        self.reader.Dispose()
        self.reader = None
        self.buffer = None

    def read(self) -> bytes:
        b = Array.CreateInstance(Byte, self.reader.UnconsumedBufferLength)
        self.reader.ReadBytes(b)
        py_b = bytes(b)
        del b
        return py_b


class BleakDataWriter:
    def __init__(self, data):
        self.data = data

    def __enter__(self):
        self.writer = DataWriter()
        self.writer.WriteBytes(Array[Byte](self.data))
        return self

    def detach_buffer(self):
        return self.writer.DetachBuffer()

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self.writer.Dispose()
        except Exception:
            pass
        del self.writer
        self.writer = None

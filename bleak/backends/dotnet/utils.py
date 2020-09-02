# -*- coding: utf-8 -*-
"""
Helper methods for awaiting on .NET Tasks.

Created on 2017-12-05 by hbldh <henrik.blidh@nedomkull.com>
"""

import asyncio

from bleak.exc import BleakDotNetTaskError

# Python for .NET CLR imports
from System import Action
from System.Threading.Tasks import Task

from Windows.Foundation import (
    AsyncOperationCompletedHandler,
    IAsyncOperation,
    AsyncStatus,
)


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


async def wrap_IAsyncOperation(op, return_type):
    """Enables await on .NET Task using asyncio.Event and a lambda callback.

    Args:
        task (System.Threading.Tasks.Task): .NET async task object to await.

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

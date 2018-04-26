# -*- coding: utf-8 -*-
"""
Helper methods for awaiting on .NET Tasks.

Created on 2017-12-05 by hbldh <henrik.blidh@nedomkull.com>
"""

import asyncio
from collections import Awaitable

from bleak.exc import BleakDotNetTaskError

# Pythonf for .NET CLR imports
from System import Action
from System.Threading.Tasks import Task


async def wrap_Task(task, loop):
    """Enables await on .NET Task using asyncio.Event and a lambda callback.

    Args:
        task (System.Threading.Tasks.Task): .NET async task object
        to await upon.
        loop (Event Loop): The event loop to await on the Task in.

    Returns:
        The results of the the .NET Task.

    """
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


class TaskWrapper(Awaitable):
    """An awaitable wrapper class for .NET Tasks."""

    def __init__(self, task, loop):
        self._loop = loop
        self.task = task
        self.done = asyncio.Event()

    def __await__(self):

        def callback(task):
            self._loop.call_soon_threadsafe(self.done.set)

        self.task.ContinueWith(Action[Task](callback))
        yield from self.done.wait()
        return self

    @property
    def result(self):
        # TODO: Handle IsCancelled.
        if self.task.IsFaulted:
            # Exception occurred. Wrap it in BleakDotNetTaskError
            # to make it catchable.
            raise BleakDotNetTaskError(self.task.Exception.ToString())

        return self.task.Result

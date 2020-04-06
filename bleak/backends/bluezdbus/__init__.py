from asyncio import AbstractEventLoop

from twisted.internet.asyncioreactor import AsyncioSelectorReactor

_reactors = {}


def get_reactor(loop: AbstractEventLoop):
    """Helper factory to get a Twisted reactor for the provided loop.

    Since the AsyncioSelectorReactor on POSIX systems leaks file descriptors
    even if stopped and presumably cleaned up, we lazily initialize them and
    cache them for each loop. In a normal use case you will only work on one
    event loop anyway, but in the case someone has different loops, this
    construct still works without leaking resources.

    Args:
        loop (asyncio.events.AbstractEventLoop): The event loop to use.

    Returns:
           A :py:class:`twisted.internet.asnycioreactor.AsyncioSelectorReactor`
           running on the provided asyncio event loop.

    """
    if loop not in _reactors:
        _reactors[loop] = AsyncioSelectorReactor(loop)

    return _reactors[loop]

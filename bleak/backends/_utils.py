import asyncio
import logging
from collections.abc import Callable
from typing import Any

from bleak._compat import TypeVarTuple, Unpack

_Ts = TypeVarTuple("_Ts")


logger = logging.getLogger(__name__)


def try_call_soon_threadsafe(
    event_loop: asyncio.AbstractEventLoop,
    callback: Callable[[Unpack[_Ts]], Any],
    *args: Unpack[_Ts],
) -> None:
    """Call a callback on the event loop thread, handling closed loop errors gracefully."""
    try:
        event_loop.call_soon_threadsafe(callback, *args)
    except RuntimeError:
        # Likely caused by loop being closed
        logger.debug("unraisable exception", exc_info=True)

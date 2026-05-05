from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    if sys.platform != "android":
        assert False, "This backend is only available on Android"

import logging
from typing import Callable

from android.content import BroadcastReceiver as _BroadcastReceiver
from android.content import Context, Intent, IntentFilter
from android.os import Handler, HandlerThread
from java import Override, jvoid, static_proxy

from bleak.backends._utils import external_thread_callback
from bleak.backends.android.utils import context

logger = logging.getLogger(__name__)


# Copied BroadcastReceiver logic from python-for-android and adapted it to chaquopy.
# See https://github.com/kivy/python-for-android/blob/6f3ab805972e0d9531e3a207a6bc51c0effd8eb9/pythonforandroid/recipes/android/src/android/broadcast.py
class BroadcastReceiver(static_proxy(_BroadcastReceiver)):  # type: ignore[misc]
    def __init__(
        self,
        callback: Callable[[Context, Intent], None],
        actions: list[str] | None = None,
        categories: list[str] | None = None,
    ):
        super(BroadcastReceiver, self).__init__()
        self.context = context
        self.callback = callback

        if not actions and not categories:
            raise Exception("You need to define at least actions or categories")

        def _expand_partial_name(partial_name: str):
            if "." in partial_name:
                return partial_name  # Its actually a full dotted name
            else:
                name = "ACTION_{}".format(partial_name.upper())
                if not hasattr(Intent, name):
                    raise Exception("The intent {} does not exist".format(name))
                return getattr(Intent, name)

        # resolve actions/categories first
        resolved_actions = [_expand_partial_name(x) for x in actions or []]
        resolved_categories = [_expand_partial_name(x) for x in categories or []]

        # create a thread for handling events from the receiver
        self.handlerthread = HandlerThread("handlerthread")

        # create a listener
        self.receiver_filter = IntentFilter()
        for x in resolved_actions:
            self.receiver_filter.addAction(x)
        for x in resolved_categories:
            self.receiver_filter.addCategory(x)

    def start(self):
        self.handlerthread.start()
        self.handler = Handler(self.handlerthread.getLooper())
        self.context.registerReceiver(
            self,
            self.receiver_filter,
            None,  # type: ignore
            self.handler,
        )

    def stop(self):
        self.context.unregisterReceiver(self)
        self.handlerthread.quit()

    @Override(jvoid, [Context, Intent])
    @external_thread_callback
    def onReceive(self, context: Context, intent: Intent):
        logger.debug(f"BroadcastReceiver received intent: {intent}")
        self.callback(context, intent)

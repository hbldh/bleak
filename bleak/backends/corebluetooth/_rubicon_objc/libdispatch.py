import ctypes

from rubicon.objc.api import ObjCInstance
from rubicon.objc.runtime import load_library, objc_id

# On Mac and iOS, libdispatch is part of libSystem.
libSystem = load_library("System")
libdispatch = libSystem

dispatch_queue_t = ctypes.c_void_p
dispatch_queue_attr_t = ctypes.c_void_p

libdispatch.dispatch_queue_create.argtypes = [ctypes.c_char_p, dispatch_queue_attr_t]
libdispatch.dispatch_queue_create.restype = dispatch_queue_t


DISPATCH_QUEUE_SERIAL: dispatch_queue_attr_t = dispatch_queue_attr_t(None)


def dispatch_queue_create(
    label: bytes, attr: dispatch_queue_attr_t
) -> dispatch_queue_t:
    queue = libdispatch.dispatch_queue_create(label, attr)
    return ObjCInstance(ctypes.cast(queue, objc_id))  # type: ignore

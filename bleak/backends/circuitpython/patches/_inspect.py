CO_COROUTINE = 0x0080


def iscoroutinefunction(obj):
    if not hasattr(obj, "__code__"):
        return False
    return (obj.__code__.co_flags & CO_COROUTINE) != 0

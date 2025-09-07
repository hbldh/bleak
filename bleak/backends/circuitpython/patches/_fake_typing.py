from collections import namedtuple

class MockType:
    """A generic mock class that can be subscribed."""

    def __getitem__(self, item):
        return self


def __getattr__(name):
    """Dynamically creates and returns a MockType for any requested attribute."""
    # This will handle common typing names like List, Dict, Optional, Any, etc.
    return MockType()


class NamedTuple:
    """Minimal NamedTuple replacement for CircuitPython."""

    def __init_subclass__(cls, **kwargs):
        annotations = getattr(cls, "__annotations__", {})
        fields = list(annotations.keys())
        print(annotations)

        if not fields:
            return

        def __init__(self, *args, **kw):
            for i, f in enumerate(fields):
                if i < len(args):
                    setattr(self, f, args[i])
                elif f in kw:
                    setattr(self, f, kw.pop(f))
                else:
                    setattr(self, f, None)
            if kw:
                raise TypeError(f"Unexpected fields: {list(kw.keys())}")

        def __repr__(self):
            parts = ", ".join(f"{f}={getattr(self,f)!r}" for f in fields)
            return f"{cls.__name__}({parts})"

        cls.__init__ = __init__
        cls.__repr__ = __repr__
        cls._fields = tuple(fields)

TypedDict = dict


TYPE_CHECKING = False


def cast(typ, val):
    return val

def assert_never(*args, **kwargs):
    return None

def override(func):
    return func

def overload(func):
    return func

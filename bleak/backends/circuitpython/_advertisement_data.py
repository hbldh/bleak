import sys

try:
    from typing import NamedTuple as _typing_namedtuple
except ImportError:
    _typing_namedtuple = None


def circuit_namedtuple(cls=None, *, annotations=None):
    if sys.implementation.name != "circuitpython":
        def passthrough(cls):
            if _typing_namedtuple is not None:
                return _typing_namedtuple(cls.__name__, [(k, v) for k, v in getattr(cls, "__annotations__", {}).items()])
            else:
                from collections import namedtuple as _collections_namedtuple
                fields = list(getattr(cls, "__annotations__", {}).keys())
                return _collections_namedtuple(cls.__name__, fields)
        return passthrough if cls is None else passthrough(cls)

    # ---- CircuitPython ----
    def wrap(cls):
        nonlocal annotations
        if annotations is None:
            raise TypeError("You must provide annotations in CircuitPython")
        fields = list(annotations.keys())

        class NT:
            __slots__ = fields

            def __init__(self, **kwargs):
                for f in fields:
                    if f in kwargs:
                        setattr(self, f, kwargs.pop(f))
                    else:
                        raise TypeError(f"Missing field {f}")
                if kwargs:
                    raise TypeError(f"Unexpected fields {list(kwargs.keys())}")

            def __repr__(self):
                values = ", ".join(f"{f}={getattr(self,f)!r}" for f in fields)
                return f"{cls.__name__}({values})"

        return NT

    return wrap if cls is None else wrap(cls)

def circuit_advertisement_data_patch(cls=None):
    annotations = {
        "local_name": "Optional[str]",
        "manufacturer_data": "dict[int, bytes]",
        "service_data": "dict[str, bytes]",
        "service_uuids": "list[str]",
        "tx_power": "Optional[int]",
        "rssi": "int",
        "platform_data": "tuple[Any, ...]",
    }
    return circuit_namedtuple(cls, annotations=annotations)

import sys
from collections.abc import Sized
from typing import Protocol

if sys.version_info < (3, 12):
    # mypy and pyright object to Buffer being both ABC and Protocol. Work around
    # by just inheriting from Protocol here. typing_extensions.Buffer is just
    # abc.ABC.
    class BufferProtocol(Protocol):
        def __buffer__(self, flags: int, /) -> memoryview: ...

else:
    from collections.abc import Buffer as BufferProtocol


class SizedBuffer(BufferProtocol, Sized, Protocol):
    """
    Protocol for types that are both Buffer and Sized.

    .. versionadded:: 2.1
    """

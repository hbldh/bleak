"""
Python version compatibility imports.

These will be removed when support for older Python versions is dropped.
"""

import sys

if sys.version_info < (3, 11):
    from async_timeout import timeout as timeout
    from typing_extensions import Never as Never
    from typing_extensions import Self as Self
    from typing_extensions import TypeVarTuple as TypeVarTuple
    from typing_extensions import Unpack as Unpack
    from typing_extensions import assert_never as assert_never
else:
    from asyncio import timeout as timeout  # noqa: F401
    from typing import Never as Never  # noqa: F401
    from typing import Self as Self  # noqa: F401
    from typing import TypeVarTuple as TypeVarTuple  # noqa: F401
    from typing import Unpack as Unpack  # noqa: F401
    from typing import assert_never as assert_never  # noqa: F401

if sys.version_info < (3, 12):
    from typing_extensions import override as override
else:
    from typing import override as override  # noqa: F401

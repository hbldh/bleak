"""
Python version compatibility imports.

These will be removed when support for older Python versions is dropped.
"""

import sys

if sys.version_info < (3, 12):
    from typing_extensions import override as override
else:
    from typing import override as override  # noqa: F401

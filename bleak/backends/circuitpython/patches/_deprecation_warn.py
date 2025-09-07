"""
This module defines DeprecationWarning for CircuitPython environments
where the warnings module is limited.
"""

try:
    DeprecationWarning
except NameError:
    # on circuitpython
    class DeprecationWarning(Warning):
        pass

import ctypes
from enum import IntEnum
from typing import Tuple

from ...exc import BleakError


def _check_hresult(result, func, args):
    if result:
        raise ctypes.WinError(result)

    return args


# https://learn.microsoft.com/en-us/windows/win32/api/combaseapi/nf-combaseapi-cogetapartmenttype
_CoGetApartmentType = ctypes.windll.ole32.CoGetApartmentType
_CoGetApartmentType.restype = ctypes.c_int
_CoGetApartmentType.argtypes = [
    ctypes.POINTER(ctypes.c_int),
    ctypes.POINTER(ctypes.c_int),
]
_CoGetApartmentType.errcheck = _check_hresult

_CO_E_NOTINITIALIZED = -2147221008


# https://learn.microsoft.com/en-us/windows/win32/api/objidl/ne-objidl-apttype
class _AptType(IntEnum):
    CURRENT = -1
    STA = 0
    MTA = 1
    NA = 2
    MAIN_STA = 3


# https://learn.microsoft.com/en-us/windows/win32/api/objidl/ne-objidl-apttypequalifier
class _AptQualifierType(IntEnum):
    NONE = 0
    IMPLICIT_MTA = 1
    NA_ON_MTA = 2
    NA_ON_STA = 3
    NA_ON_IMPLICIT_STA = 4
    NA_ON_MAIN_STA = 5
    APPLICATION_STA = 6
    RESERVED_1 = 7


def _get_apartment_type() -> Tuple[_AptType, _AptQualifierType]:
    """
    Calls CoGetApartmentType to get the current apartment type and qualifier.

    Returns:
        The current apartment type and qualifier.
    Raises:
        OSError: If the call to CoGetApartmentType fails.
    """
    api_type = ctypes.c_int()
    api_type_qualifier = ctypes.c_int()
    _CoGetApartmentType(ctypes.byref(api_type), ctypes.byref(api_type_qualifier))
    return _AptType(api_type.value), _AptQualifierType(api_type_qualifier.value)


def assert_mta() -> None:
    """
    Asserts that the current apartment type is MTA.

    Raises:
        BleakError: If the current apartment type is not MTA.

    .. versionadded:: 0.22
    """
    if hasattr(allow_sta, "_allowed"):
        return

    try:
        apt_type, _ = _get_apartment_type()
        if apt_type != _AptType.MTA:
            raise BleakError(
                f"The current thread apartment type is not MTA: {apt_type.name}. Beware of packages like pywin32 that may change the apartment type implicitly."
            )
    except OSError as e:
        # All is OK if not initialized yet. WinRT will initialize it.
        if e.winerror != _CO_E_NOTINITIALIZED:
            raise


def allow_sta():
    """
    Suppress check for MTA thread type and allow STA.

    Bleak will hang forever if the current thread is not MTA - unless there is
    a Windows event loop running that is properly integrated with asyncio in
    Python.

    If your program meets that condition, you must call this function do disable
    the check for MTA. If your program doesn't have a graphical user interface
    you probably shouldn't call this function. and use ``uninitialize_sta()``
    instead.

    .. versionadded:: 0.22.1
    """
    allow_sta._allowed = True


def uninitialize_sta():
    """
    Uninitialize the COM library on the current thread if it was not initialized
    as MTA.

    This is intended to undo the implicit initialization of the COM library as STA
    by packages like pywin32.

    It should be called as early as possible in your application after the
    offending package has been imported.

    .. versionadded:: 0.22
    """
    try:
        assert_mta()
    except BleakError:
        ctypes.windll.ole32.CoUninitialize()

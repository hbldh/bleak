# from _bleio import UUID as _IO_UUID
# from adafruit_ble.uuid import UUID as _UUID, VendorUUID, StandardUUID
from adafruit_ble.uuid import VendorUUID, StandardUUID
from _bleio import UUID

assert UUID
assert VendorUUID
assert StandardUUID

# class UUID(_UUID):
#
#     def __init__(self, value):
#         self.bleio_uuid = _IO_UUID(value)
#         self.size = 16
#
#     def __str__(self) -> str:
#         return (
#             "{:02x}{:02x}{:02x}{:02x}-"  # pylint: disable=consider-using-f-string
#             "{:02x}{:02x}-"
#             "{:02x}{:02x}-"
#             "{:02x}{:02x}-"
#             "{:02x}{:02x}{:02x}{:02x}{:02x}{:02x}"
#         ).format(*reversed(self.bleio_uuid.uuid128))

from enum import IntEnum 

class UserRolesEnum(IntEnum):
    "Integer Enum for user roles."
    GUEST = 0
    STANDARD = 1
    CURATOR = 2
    ADMIN = 4
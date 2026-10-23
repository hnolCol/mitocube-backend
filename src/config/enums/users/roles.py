from enum import IntEnum 

class UserRolesEnum(IntEnum):
    "Integer Enum for user roles."
    GUEST = 0
    STANDARD = 1
    GROUP_CURATOR = 2
    CURATOR = 3
    ADMIN = 4

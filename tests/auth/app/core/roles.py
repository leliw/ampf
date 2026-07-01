from enum import StrEnum


class Role(StrEnum):
    ADMIN = "admin"


ROLE_DESCRIPTIONS = {
    Role.ADMIN: "Admin",
}

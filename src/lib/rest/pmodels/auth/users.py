from datetime import datetime
from typing import List

from pydantic import BaseModel, EmailStr, Field, field_validator, SecretStr

# from api.pmodels.application import BasePRM

class UserPM(BaseModel):  # Mix of former BasicUser, BasicUserWithEmail and some parts of former UserModel; PM PydanticModel
    """The very basic user information"""
    id: int | None = None  # ToDo: Never allowed to be None? just for GUI at the moment
    label: str = Field(..., min_length = 8, max_length = 8, default_factory = lambda : "12345678")  # ToDo: get_random_string(8)) # ToDo: rename to username
    firstname: str | None = None
    lastname: str | None = None
    email: EmailStr | None = None  # Question: why extra email user PM in the old code? could be None if not needed?
    institute: str | None = None  # ToDo: Not in User directly comes from SQL table sec_research_groups.institute, # Question: Can one save PMs here?
    research_group: str | None = None  # ToDo: Not in User directly comes from SQL table sec_research_groups.research_group # Question: Can one save PMs here?
    created_on: datetime = datetime.now()
    updated_on: datetime = datetime.now()

    # ToDo: Implement the following missing, or create ABCUserPM
    # research_group_id Optional
    # image
    # profile_text
    # orcid
    # url
    # updated_on
    # last_login_on

    @field_validator("email")
    def validate_email_string(self, email: EmailStr) -> EmailStr:
        # ToDo: Implement at least simple email validation
        if not any(email.endswith("@" + domain) for domain in ["ukbonn.de", "uni-bonn.de"]):  # ToDo: Move to CONFIG, counter check if something@some"@"thing.else is theoretically valid, or something@something.else(@ukbonn.de)
            raise ValueError("Email address is not from an white listed domain. Please contact your administrator.")
        return email

class AuthUserPM(UserPM):  # Basically former UserModel; PM PydanticModel
    """BaseModel for a user"""
    agreed_to_terms: bool | None = None  # ToDo: Not in DB yet
    expires_after: float | None = None
    password: SecretStr = None
    salt: SecretStr | None = None
    allow_login: bool = False
    role: int = 1  # UserRolesEnum = UserRolesEnum.STANDARD  # ToDo: Not in user directly. comes from SQL sec_permission_groups and sec_nm_permission_users


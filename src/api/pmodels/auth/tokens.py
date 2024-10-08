from datetime import datetime
from typing import List

from pydantic import EmailStr, Field, field_validator, SecretStr

from api.pmodels.application import BasePRM

class TokenVerificationCodePPM(BasePRM):  # Former TokenVerificationCode; PPM ~ Pydantic Post/Get Model
    """Validation Code for Specific UserModel Token"""
    verification_code : str  #= Field(...,default_factory=lambda : get_random_string(N = 12))


class UserTokenPRM(BasePRM):  # Former TokenResponse; PRM ~ Pydantic Response Model
    """Response Model for a valid login."""
    success: bool   # Question: what is it for? move that to FrontendPResponseModel as basic message?
    token: str  # move that to PResponseModel as basic message?

    verified: bool = False  # Question, would remove that, rather failed login if not verified
    role: int = 0  # former UserRolesEnum GUEST = 0 - STANDARD = 1 - CURATOR = 2 - ADMIN = 4  # Question: good to display role, but to verfiy own function and raise Exception?
    label: str | None = None  # Question, remove and replace with id (below) or rename to username  # Fixme: Why? Input should be a valid string
    id: int | None  # Alternative to label above, or treat label as username?
    firstname: str | None = None  # Question: Why is it needed here?
    lastname: str | None = None  # Question: Why is it needed here?

class ValidUserTokenValidPRM(BasePRM):  # Former TokenValidResponse; PRM ~ Pydantic Response Model
    """Response model for a valid token"""
    success: bool  # Question: what is it for? move that to FrontendPResponseModel as basic message?

    role: int = 0  # former UserRolesEnum GUEST = 0 - STANDARD = 1 - CURATOR = 2 - ADMIN = 4  # Question: good to display role, but to verfiy own function and raise Exception?
    verified: bool = False  # Question, would remove that, rather failed login if not verified
    firstname: str | None = None  # Question: Why is it needed here?
    lastname: str | None = None  # Question: Why is it needed here?
    label: str | None = None  # Question, remove and replace with id (below) or rename to username
    id: int | None = None  # Alternative to label above, or treat label as username?

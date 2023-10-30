from pydantic import BaseModel 
from pydantic import Field
from typing import Optional

from config.enums.users.roles import UserRolesEnum 
from services.random_generators import get_random_string

class Token(BaseModel):
    """Token response model"""
    access_token : str
    token_type : str = "Bearer"

class TokenVerificationCode(BaseModel):
    """Validation Code for Specific User Token"""
    verification_code : str #= Field(...,default_factory=lambda : get_random_string(N = 12))

class ShareTokenPassword(BaseModel):
    """"""
    pw : str

class TokenResponse(BaseModel):
    """Response Model for a valid login."""
    success : bool 
    token : str 
    
    verified : bool = False
    role : UserRolesEnum = 0
    label : Optional[str] = None
    firstname : Optional[str] = None
    lastname : Optional[str]  = None
    msg : Optional[str] = None 


class TokenValidResponse(BaseModel):
    """Response model for a valid token"""
    success : bool
    role : UserRolesEnum = 0
    verified : bool = False
    firstname : str 
    lastname : str 
    label : str
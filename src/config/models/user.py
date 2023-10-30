from pydantic import BaseModel 
from pydantic import Field
from pydantic import EmailStr 
from pydantic import SecretStr
from pydantic import field_validator
from pydantic import field_serializer
from datetime import datetime
from typing import List 
import time 

from config.settings.general import get_general_settings
from config.enums.users.roles import UserRolesEnum
from services.random_generators import get_random_string
from services.enums import get_inversed_enum_as_dict
import time 

GENERAL_SETTINGS = get_general_settings()


class BasicUser(BaseModel):
    """The very basic user information"""
    
    firstname : str 
    lastname : str 
    institute : str 
    research_group : str 
    created_on : float = Field(default_factory=time.time)


class User(BasicUser):
    """BaseModel for a user"""
    id : int
    label : str = Field(...,min_length=8,max_length=8,default_factory=lambda : get_random_string(8))
    email : EmailStr 
    updated_on : float  = None 
    expires_after : float = None
    password : SecretStr = None
    allow_login : bool = True 
    role : UserRolesEnum = UserRolesEnum.STANDARD
    salt : str = None
    # image : bytearray = None

    @field_validator("email")
    def check_email_domain(cls, v: EmailStr) -> EmailStr:
        """Checks if email domain is allowed"""
        if not any(v.endswith(email_domain) for email_domain in GENERAL_SETTINGS.allowed_email_domains):
            raise ValueError("Email adresses must end with an allowed domain. Please contact your administrator.")
        return v 
    

class AdminUserView(BasicUser):
    """"""
    id : int
    label : str = Field(...,min_length=8,max_length=8,default_factory=lambda : get_random_string(8))
    email : EmailStr 
    allow_login : bool
    role : UserRolesEnum

    # @field_serializer("created_on")
    # def dt_to_timestamp(dt : datetime):
    #     ""
    #     return dt.timestamp()

class UsersAdminResponse(BaseModel):
    """API Admin Response"""
    users : List[AdminUserView]
    roles : dict = Field(default_factory=lambda : get_inversed_enum_as_dict(UserRolesEnum))

class PublicUser(BaseModel):
    """
    Public BaseModel for a User. 
    Public indicates user info to be seen by other users.
    To distinguish them, the API deadend for those is /api/collaborators
    while api/users is restricted to admin rights. 
    """
    label : str
    firstname : str
    lastname : str 
    research_group : str 
    institute : str 
    email : EmailStr



class Collaborators(BaseModel):
    users : List[PublicUser]

#user_dict = DB().get_user_by_id(id="asdada")


   


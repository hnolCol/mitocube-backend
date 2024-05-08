from pydantic import BaseModel 
from pydantic import Field
from pydantic import EmailStr 
from pydantic import SecretStr
from pydantic import field_validator
from pydantic import field_serializer, model_serializer
from datetime import datetime
from typing import List, Optional
import time 

from config.settings.general import get_general_settings
from config.models.attributes import AttributeValueModel
from config.enums.users.roles import UserRolesEnum
from services.random_generators import get_random_string
from services.enums import get_inversed_enum_as_dict
import time 

GENERAL_SETTINGS = get_general_settings()


class BasicUser(BaseModel):
    """The very basic user information"""
    #label : str = Field(...,min_length=8,max_length=8,default_factory=lambda : get_random_string(8))
    tag : str = Field(...,min_length=8,max_length=8,default_factory=lambda : get_random_string(8))
    firstname : str 
    lastname : str 
    institute : str 
    research_group : str 
    created_on : float = Field(default_factory=time.time)

class BasicUserWithEmail(BasicUser):
    """
    """
    email : EmailStr 
    @field_validator("email")
    def check_email_domain(cls, v: EmailStr) -> EmailStr:
        """Checks if email domain is allowed"""
        if not any(v.endswith(email_domain) for email_domain in GENERAL_SETTINGS.allowed_email_domains):
            raise ValueError("Email adresses must end with an allowed domain. Please contact your administrator.")
        return v 

class UserModel(BasicUserWithEmail):
    """BaseModel for a user"""
    updated_on : float = None
    agreed_to_terms : Optional[bool] = None
    expires_after : float = None
    password : SecretStr = None
    allow_login : bool = True 
    role : UserRolesEnum = UserRolesEnum.STANDARD
    #salt : str = None


    
class UserModelForRegistration(BasicUserWithEmail):
    """"""
    password : SecretStr = Field(default_factory=lambda : get_random_string(10)) #generate a random password upon generation, will be send via email to user
    role : UserRolesEnum = UserRolesEnum.STANDARD

    @field_validator("role",mode="before")
    def validate_role(v : str):
        """From a post request"""
        return int(v)


class AddUserPropsModel(BaseModel):
    """BaseModel that handles the 
    attribute based user input. Upon sterilization (model_dump())
    a UserModel is created which automatically validates the input. 

    Parameters
    ----------
    att_user_firstname 
    att_user_lastname
    att_user_institute
    att_user_research_group
    att_user_email 
    att_user_role 
    """
    att_user_firstname : str 
    att_user_lastname : str 
    att_user_institute : AttributeValueModel
    att_user_research_group : AttributeValueModel
    att_user_email : EmailStr
    att_user_role : UserRolesEnum = UserRolesEnum.STANDARD

    @model_serializer()
    def serialize_model(self):
        return UserModel(
            email=self.att_user_email,
            firstname=self.att_user_firstname,
            lastname=self.att_user_lastname,
            role = self.att_user_role,
            research_group= self.att_user_research_group.text,
            institute=self.att_user_institute.text
        ).model_dump(exclude_none=True)
    

class UserModelForUpdate(BaseModel):
    """"""
    label : str = Field(...,min_length=8, max_length=8)
    firstname : str 
    lastname : str 
    institute : str 
    research_group : str 
    role : UserRolesEnum
    updated_on : float = Field(default_factory=time.time)


class AdminUserView(BasicUser):
    """"""
    #id : int
    email : EmailStr 
    allow_login : bool
    role : UserRolesEnum

class UsersAdminResponse(BaseModel):
    """API Admin Response"""
    users : List[AdminUserView]
    roles : dict = Field(default_factory=lambda : get_inversed_enum_as_dict(UserRolesEnum))

class PublicUser(BaseModel):
    """
    Public BaseModel for a UserModel. 
    Public indicates user info to be seen by other users.
    To distinguish them, the API deadend for those is /api/collaborators
    while api/users is restricted to admin rights. 
    """
    tag : str = None
    firstname : str
    lastname : str 
    research_group : str 
    institute : str 
    email : EmailStr

class CollaboratorsResponseModel(BaseModel):
    """Collaborators Mdeol"""
    users : List[PublicUser]


class UseRoleReponseModel(BaseModel):
    """The user roles response model."""
    roles : dict = Field(default_factory=lambda : get_inversed_enum_as_dict(UserRolesEnum))


class UserLabel(BaseModel):
    """"""
    label : str = Field(...,min_length=8,max_length=8)


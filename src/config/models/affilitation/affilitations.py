
from pydantic import BaseModel
from pydantic import Field 
from pydantic import EmailStr 

from typing import Optional

from services.random_generators import get_random_string

class Institute(BaseModel):
    """Base Model to define an Institute"""
    id : str = Field(default_factory=get_random_string)
    name : str 
    postal_code : str
    city : str
    street : Optional[str]
    lead_contact : Optional[EmailStr]
    description : Optional[str] 


class Group(BaseModel):
    """Base Model that defines a group at an Institute"""
    id : str = Field(default_factory=get_random_string)
    name : str 
    institute_name : str 
    address : Optional[str]
    lead_contact : Optional[EmailStr]
    description : Optional[str] 
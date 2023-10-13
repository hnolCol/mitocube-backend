from pydantic import BaseModel
from pydantic import Field 
from pydantic import field_validator
from typing import Any, Optional


from services.random_generators import get_random_string

class Attribute(BaseModel):
    """BaseModel for Attributes"""
    id : int
    tag : str 
    description : str = None
    priority : int = 1 #attributes will be sorted by priority in descending order
    parent_tag : Optional[str] = None #parent attribute shoudl be Attribute type
    allow_as_qc : bool = True #attributes that are required for qc runs 
    allow_as_filter : bool = True #attributes allow to filter datasets
    allow_for_measurement : bool = True #atributes that are required when state of projekt changes to measuring

    @field_validator("tag")
    @classmethod
    def check_tag(cls, v : str) -> str:
        """Checks the tag of an attribute and """
        if not v.startswith("att_"):
            raise ValueError("Attribute Tags must start 'att_'. Example : 'att_organism")
        return v.lower()


class AttributeValue(BaseModel):
    """BaseModel a attribute"""
    id : int
    type : Attribute 
    tag : str 


    @field_validator("tag")
    @classmethod
    def check_tag(cls, v : str) -> str:
        """Checks tags to contain att_ and a :"""
        if not v.startswith("att_"):
            raise ValueError("AttributeValue Tags must start 'att_'. Example : 'att_organism")
        if not ":" in v and not v.endswith(":"): #make sure tag is not empty after : 
            raise ValueError("AttributeValue tags must follow the the pattern <attribute_tag>:<attribute_value>")
        if len(v.split(":")) != 2:
            raise ValueError("Tag must canontain exactly one ':'")
        return v.lower()


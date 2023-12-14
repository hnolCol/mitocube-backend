from pydantic import BaseModel
from pydantic import Field 
from pydantic import field_validator
from pydantic import field_serializer
from typing import Any, Optional, List
import numpy as np 

from services.random_generators import get_random_string

class Attribute(BaseModel):
    """BaseModel for Attributes"""
    id : int
    tag : str 
    text : str 
    priority : int = 500 #attributes will be sorted by priority in descending order
    parent_id : Optional[int] = None #parent attribute shoudl be Attribute type
    parent_tag : Optional[str] = None #parent tag 
    group_tag : str # attrbiute grouping
    mandatory_for_submission : bool = False #must be defined by an attribute value for a submission
    mandatory_for_active : bool = False #must be defined by an attribute value for an active (published) state 
    has_features_value : bool = False #if true, features (e.g. proteins) can be selected for this attribute 
    has_numeric_input : bool = False #if true, attribute can be defined by the user (numeric input)
    min_state : int = 0 #The minimal state the submission must have in order to define the attribute. 
    allow_as_qc : bool = True #attributes that are required for qc runs 
    allow_as_filter : bool = True #attributes allow to filter datasets
    allow_for_measurement : bool = True #atributes that are required when state of projekt changes to measuring
    allow_for_genotype : bool = False #attributes that are allowed for specifiying a genotype.
    allow_for_dataset : bool = False #allow to use this attribute to define a dataset. 
    allow_for_user : bool = False

    @field_validator('parent_id', mode="before")
    def change_nan_to_none(cls, v, field):
        """
        Check input for parent_id as pandas dataframe will transform
        it to a float if there is null/None (e.g. NaN)
        """
        if v is None: return None
        
        if np.isnan(v):
            return None
        return int(v)

    @field_validator('parent_id', mode="before")
    def change_nan_to_none(cls, v, field):
        """
        Check input for parent_id as pandas dataframe will transform
        it to a float if there is null/None (e.g. NaN)
        """
        if v is None: return None
        
        if np.isnan(v):
            return None
        return int(v)

    @field_serializer("parent_id", mode="plain")
    def check_parent_id(v : int):
        if v is None: return v 
        if np.isnan(v): return None
        return v 

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
    attribute_id : int
    text : str
    tag : str 
    description : Optional[str] = ""
    
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
    
    @field_validator("text", mode="before")
    @classmethod
    def check_name(cls, v : Any) -> str:
        """Checks text to be string"""
        if not isinstance(v,str): return str(v)
        else: return v 

class AttributeResponse(BaseModel):
    """Response model for receiving attributes."""
    attributes : List[Attribute]
    attribute_values : List[AttributeValue]
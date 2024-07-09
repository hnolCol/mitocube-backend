from pydantic import BaseModel, field_validator, field_serializer

from typing import Any, Optional, List, Union, Literal
import numpy as np 
from config.models.feature import FeatureNeoModel
# from services.random_generators import get_random_string

class AttributeModel(BaseModel):
    """
    BaseModel for Attributes
    id : int 
        The identifier of the attribute
    tag : str 
        Attribute tag, is validated to be of style ``att_<text>``
    text : str
        Attribute text to be displayed to a user in a ui. 
    priority : int, default 500 
        Priority of the attribute 
    parent_id : int, optional, default None
        The id of the parent attribute. Use for visualization in the ui.  
    parent_tag : str, optional, default None
        Tag tag of the parent attribute. 
    group_tag : str 
        Specifying the type of attribute. This is used to visualize the attribute based filtering. 
    mandatory_for_submission : bool, default False
        If true, the attribute must be defined upon submission of a new project.
    mandatory_for_active : bool, default False 
        If true, the attribute must be defined before the data of the dataset can be explored. 
    has_feature_value : bool, default False 
        If true, the attribute_values are the features (proteins) present in the database 
    has_numeric_input : bool, default False 
        If true, the attribute can be defined by a simple numeric value (e.g. attribute_value). 
    min_state : int, default 0
        The minimal state defined in ``SubmissionStatesEnums`` the submission must be in to allow the attribute
        to be defined. For example, upon changing the submission to ``MEASURING`` the mass spectrometer should be defined. 
        But this information is not yet available at submission. 
    allow_as_qc : bool, default False
        Allow the attribute for quality control 
    allow_as_filter : bool, default True
        If True, the attribute can be used to filter datasets/submissions. 
    allow_for_dataset : bool, default False 
        If True, the attribute can be used to define a dataset. 
    allow_for_user : bool, default False 
        If true, the attribute can be used to define a user. 
        
    has_unit : bool, default False
        If true, the user can define a unit for the attribute.
    
    unit : Literal["weight","concentration", "time","temperature","volume","masstocharge","voltage","flow","arbitrary"], default None
        The unit type
    """
    id : int
    tag : str 
    text : str 
    priority : int = 500  # attributes will be sorted by priority in descending order
    parent_id : Optional[int] = None  # parent attribute should be Attribute type
    parent_tag : Optional[str] = None  # parent tag
    group_tag : str  # attribute grouping
    s : Optional[str] = None
    mandatory_for_submission : bool = False  # must be defined by an attribute value for a submission
    mandatory_for_active : bool = False  # must be defined by an attribute value for an active (published) state
    has_features_value : bool = False  # if true, features (e.g. proteins) can be selected for this attribute
    has_numeric_input : bool = False  # if true, attribute can be defined by the user (numeric input)
    min_state : int = 0  # The minimal state the submission must have in order to define the attribute.
    allow_as_qc : bool = False  # attributes that are required for qc runs
    allow_as_filter : bool = True  # attributes allow to filter datasets
    allow_for_measurement : bool = True  # attribute that are required when state of project changes to measuring, ToDO: I think this is covered by min_state? 
    allow_for_genotype : bool = False  # attributes that are allowed for specifying a genotype.
    allow_for_dataset : bool = False  # allow to use this attribute to define a dataset.
    allow_for_user : bool = False
    has_unit : bool = False 
    unit : Optional[List[Literal["weight","concentration", "time","temperature","volume","masstocharge","voltage","flow","arbitrary"]]] = None # ToDo: define units like this? 


    @field_validator('s', mode="before")
    def check_search(cls, v : List[str]|str, field):
        ""
        if v is None: return ""
        if isinstance(v,str): return v 
        return " ".join([str(s).lower() for s in v if s is not None])
        
    @field_validator('unit', mode="before")
    def check_unit(cls, v : str|List[str], field):
        if isinstance(v,str): return v.split(";")
        if isinstance(v,list): return v 
        return None 

    @field_validator('parent_id', mode="before")
    def change_nan_to_none(cls, v, field):  # ToDo: cls or self? @classmethod
        """
        Check input for parent_id as pandas dataframe will transform
        it to a float if there is null/None (e.g. NaN)
        """
        if v is None:
            return None
        
        if np.isnan(v):
            return None

        return int(v)

    @field_validator('parent_id', mode="before")
    @classmethod
    def change_nan_to_none(cls, v, field): 
        """
        Check input for parent_id as pandas dataframe will transform
        it to a float if there is null/None (e.g. NaN)
        """
        if v is None:
            return None
        
        if np.isnan(v):
            return None

        return int(v)

    @field_serializer("parent_id", mode="plain")
    def check_parent_id(self, v : int):  # ToDo: Missing self? :: I think, pydantic docs uses cls for validator, self for serilizer
        if v is None:
            return v

        if np.isnan(v):
            return None

        return v 

    @field_validator("tag")  # ToDo, issue with return type?
    @classmethod
    def check_tag(cls, v : str) -> str:
        """Checks the tag of an attribute and """
        if not v.startswith("att_"):
            raise ValueError("Attribute Tags must start 'att_'. Example : 'att_organism")
        return v #remove lower, otherwise proteome maps are inconsistent


class AttributeValueModel(BaseModel):  # ToDo: Update, add value and feature_id (check definitions first)
    """
    BaseModel for an attribute value
    
    Parameters
    ----------

    id : int 
        ID of the attribute value
    attribute_id : int 
        ID of the attribute the value belongs to.
    text : str 
        String representative of the value
    value : str,float,int 
        The actual value 
    description : str, optional, default ""
        Description of the attribute value. 
    """
    #id : int
    #attribute_id : int
    attribute_tag : Optional[str] = None 
    text : str
    tag : str 
    unit_value : Optional[float] = None # The value associated with the attribute value, often None, for some we can define a certain unit value such as concentration 
    #value : float  # ToDo: str or float or int? or more flexible? :: The excel table says attribute_value, value is not a float then, maybe like
    #value : Optional[Union[float,str,int]] #maybe like this? #changed the excel header attribute_value to value since attribute_id referece to the attribute not the attribute value
    description : Optional[str] = ""
    s : str = None #The search param 
    #feature : Optional[str] = None #feature_key 
    
   # feature : str # i dont understand feature here, in my view the attribute_value becomes the feature ID, but I we probably dont need this anymore and we should use the FeatureModel instead. 
    @field_validator('s', mode="before")
    def check_search(cls, v : List[str]|str, field):
        ""
        if v is None: return ""
        if isinstance(v,str): return v 
        return " ".join([str(s).lower() for s in v if s is not None])
    
    @field_validator("text", mode="before")  # ToDo, issue with return type?
    @classmethod
    def check_name(cls, v : Any) -> str:
        """Checks text to be string"""
        if not isinstance(v,str):
            return str(v)
        else:
            return v


class AttributeValuesByDatasetModel(BaseModel):
    attribute_value : AttributeValueModel|FeatureNeoModel
    tags : List[str]
    count : int 


class AttributeResponseModel(BaseModel):
    """
    Response model for receiving attributes.
    Parameters
    ----------
    attributes : List[AttributeModel]
        The list of of attributes stored in the database. 

    attribute_values : List[AttributeValueModel]
        The list of attribute_values. 
    """
    attributes : List[AttributeModel]
    attribute_values : List[AttributeValueModel]


class SampleAttributes(BaseModel):
    """Model that describes the sample attributes 

    Parameters
    ----------
    BaseModel : _type_
        _description_
    """
    
    attribute_tags : List[str] 

class AttributeUnitModel(BaseModel):
    tag : str 
    text : str     
    unit : str  

class AttributeUnitResponseModel(BaseModel):
    attribute : AttributeModel
    units : List[AttributeUnitModel]


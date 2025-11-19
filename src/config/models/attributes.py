from pydantic import BaseModel, field_validator, field_serializer

from typing import Any, Optional, List, Union, Literal, ForwardRef, Dict
import numpy as np 
from config.models.feature import FeatureNeoModel

from config.enums.units import UnitsEnum
from config.models.unit import UnitInputResponseModel




AttributeTree = ForwardRef('AttributeTree')
    
class AttributeTree(BaseModel):
    """Describes a tree structure of attributes and traits. 
    This structure is excepted from the frontend when inserting genetic and condition applications.
    This is used for genetic applications and and condition applications"""
    
    tag : str # Attribute or Trait String 
    type :  Literal["attribute","trait"]
    value : Optional[float|int|str] = None
    children : Optional[List[AttributeTree]]
    
class AttributeBaseModel(BaseModel):
    """Base model for all attributes.

    Parameters
    ----------
    BaseModel : _type_
        _description_

    Returns
    -------
    _type_
        _description_

    Raises
    ------
    ValueError
        _description_
    """
    tag : str 
    text : str
    priority : int = 500  # attributes will be sorted by priority in descending order

class AttributeModel(AttributeBaseModel):

    """
    BaseModel for Attributes
    id : int 
        The identifier of the attribute
    tag : str 
        Attribute tag, is validated to be of style ``att_<text>``
    text : str
        Attribute text to be displayed to a user in a ui. 
    type : str, default None
        
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
    allow_for_qc : bool, default False
        Allow the attribute for quality control 
    allow_as_filter : bool, default True
        If True, the attribute can be used to filter datasets/submissions. 
    allow_for_dataset : bool, default False 
        If True, the attribute can be used to define a dataset. 
    allow_for_user : bool, default False 
        If true, the attribute can be used to define a user. 
        
    has_unit : bool, default False
        If true, the user can define a unit for the attribute.
    
    unit : Literal["mass","concentration", "time","temperature","volume","masstocharge","voltage","flow rate","arbitrary","fraction"], default None
        The unit type
    """
    
    parent_tag : Optional[str] = None  # parent tag
    group_tag : str  # attribute grouping
    s : Optional[str] = None # search string (no caps)
    children : Optional[List[str]] = None# list of strings that are children of this attribute (for example if an attribute has values to be entered by the user, the attribute must have UnitAttributes as children.)
    allow_input : bool #if the attribute allows for data input by the user. For example, a concentration.
    has_features_value : Optional[bool] = False  # if true, features (e.g. proteins) can be selected for this attribute
    has_numeric_input : Optional[bool] = False  # if true, attribute can be defined by the user (numeric input)
    min_state : int = 0  # The minimal state the submission must have in order to define the attribute.
   
    
    class Config:  
        use_enum_values = True

    @field_validator('s', mode="before")
    def check_search(cls, v : List[str]|str, field):
        ""
        if v is None: return ""
        if isinstance(v,str): return v 
        return " ".join([str(s).lower() for s in v if s is not None])
    
    @field_validator('children', mode="before")
    def check_children(cls, v : List[str]|str, field):
        ""
        if v is None: return None
        if isinstance(v,list): return v 
        if isinstance(v,str): return v.split("|")
        print(f"Warning: children should be a list of strings, got {type(v)}, input {v}. Converting to empty list.")
        return []
        
    
    # @field_validator('unit', mode="before")
    # def check_unit(cls, v : str|List[str], field):
    #     if isinstance(v,str): return v.split(";")
    #     if isinstance(v,list): return v 
    #     return None 

    # @field_validator('parent_id', mode="before")
    # def change_nan_to_none(cls, v, field):  # ToDo: cls or self? @classmethod
    #     """
    #     Check input for parent_id as pandas dataframe will transform
    #     it to a float if there is null/None (e.g. NaN)
    #     """
    #     if v is None:
    #         return None
        
    #     if np.isnan(v):
    #         return None

    #     return int(v)

    # @field_validator('parent_id', mode="before")
    # @classmethod
    # def change_nan_to_none(cls, v, field): 
    #     """
    #     Check input for parent_id as pandas dataframe will transform
    #     it to a float if there is null/None (e.g. NaN)
    #     """
    #     if v is None:
    #         return None
        
    #     if np.isnan(v):
    #         return None

    #     return int(v)

    # @field_serializer("parent_id", mode="plain")
    # def check_parent_id(self, v : int):  # ToDo: Missing self? :: I think, pydantic docs uses cls for validator, self for serilizer
    #     if v is None:
    #         return v

    #     if np.isnan(v):
    #         return None

    #     return v 

    @field_validator("tag")  # ToDo, issue with return type?
    @classmethod
    def check_tag(cls, v : str) -> str:
        """Checks the tag of an attribute and """
        if not v.startswith("att_"):
            raise ValueError("Attribute Tags must start 'att_'. Example : 'att_organism")
        return str(v)




class AttributeResponseModel(AttributeBaseModel):
    allow_input : bool = False  # if the attribute allows for data input by the user. For example, a concentration.


AttributeTreeNode = ForwardRef('AttributeTreeNode')
class AttributeTreeNode(BaseModel):
    """_summary_

    Parameters
    ----------
    BaseModel : _type_
        _description_

    Returns
    -------
    _type_
        _description_
    """
    
    tag : str 
    priority : int
    min_state : int
    IS_PARENT_OF : Optional[List[AttributeTreeNode]] = []


# AttributeTreeNode.model_rebuild()


# print(AttributeTreeNode)

class TraitUnitInput(BaseModel):
    unit_tag : str 
    unit_text : str 
    value : Union[str,float,int]

class TraitBaseModel(BaseModel):
    """
    BaseModel for an attribute value
    
    Parameters
    ----------

    text : str 
        String representative of the value
    value : str,float,int 
        The actual value 
    description : str, optional, default ""
        Description of the attribute value. 
    """
    attribute_tag : Optional[str] = None 
    text : str
    tag : str 
    description : Optional[str] = ""
class TraitModel(TraitBaseModel):
    """
    BaseModel for a trait
    """
    s : str = None #The search param 
    
    @field_validator('s', mode="before")
    def check_search(cls, v : List[str]|str, field):
        ""
        if v is None: return ""
        if isinstance(v,str): return v 
        return " ".join([str(s).lower() for s in v if s is not None])
    
    @field_validator("text", mode="before")  
    @classmethod
    def check_text(cls, v : Any) -> str:
        """Checks text to be string"""
        if not isinstance(v,str):
            return str(v)
        else:
            return v
        
class TraitResponseModel(TraitBaseModel):
    ""
    
    
    
class AttributeValueModel(BaseModel):  # ToDo: Update, add value and feature_id (check definitions first)
    """
    BaseModel for an attribute value
    
    Parameters
    ----------

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
    #unit_value : Optional[float] = None # The value associated with the attribute value, often None, for some we can define a certain unit value such as concentration 
    #value : float  # ToDo: str or float or int? or more flexible? :: The excel table says attribute_value, value is not a float then, maybe like
    #value : Optional[Union[float,str,int]] #maybe like this? #changed the excel header attribute_value to value since attribute_id referece to the attribute not the attribute value
    description : Optional[str] = ""
    s : str = None #The search param 
    user_input :  Optional[Dict[str,TraitUnitInput]] = None # unittype_tag -> TraitUnitInput  Optional[List[UnitInputResponseModel]] = None
    #feature : Optional[str] = None #feature_key 
    
   # feature : str # i dont understand feature here, in my view the attribute_value becomes the feature ID, but I we probably dont need this anymore and we should use the FeatureModel instead. 
    @field_validator('s', mode="before")
    def check_search(cls, v : List[str]|str, field):
        ""
        if v is None: return ""
        if isinstance(v,str): return v 
        return " ".join([str(s).lower() for s in v if s is not None])
    
    @field_validator("text", mode="before")  
    @classmethod
    def check_text(cls, v : Any) -> str:
        """Checks text to be string"""
        if not isinstance(v,str):
            return str(v)
        else:
            return v
        
    @field_validator("tag", mode="before") 
    @classmethod
    def check_tag(cls, v : Any) -> str:
        """Checks tag to be string"""
        if not isinstance(v,str):
            return str(v)
        else:
            return v
        
    @field_validator("user_input", mode="before")
    @classmethod
    def check_user_input(cls, v: Any):
        if not isinstance(v,dict): return None 
        if len(v) == 0: return None 
        if any(vi["value"] is None for vi in v.values()):
            return None 
        return v 

class AttrInput(AttributeValueModel):
    user_input :  Dict[str,TraitUnitInput]


class AttribteValueInsertModel(BaseModel):
    attribute_tag : str
    text : str 
    description : str 


class AttributeValuesBySubmissionModel(BaseModel):
    attribute_value : AttributeValueModel
    tags : List[str]
    count : int 


class AttributeTraitResponseModel(BaseModel):
    attribute: AttributeModel
    traits: List[TraitModel]

class AttributeTraitTagResponseModel(BaseModel):
    "Returns an attribute (tag) and the corresponding trait tags."
    attribute_tag: str 
    trait_tags: List[str]

# class AttributeResponseModel(BaseModel):
#     """
#     Response model for receiving attributes.
#     Parameters
#     ----------
#     attributes : List[AttributeModel]
#         The list of of attributes stored in the database. 

#     attribute_values : List[AttributeValueModel]
#         The list of attribute_values. 
#     """
#     attributes : List[AttributeModel]
#     attribute_values : List[AttributeValueModel|FeatureNeoModel]





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
    attribute_tag : str 
    unit_type_tag : str
    unit_type_text: str 
     
    # attribute : AttributeModel
    # units : List[AttributeUnitModel]



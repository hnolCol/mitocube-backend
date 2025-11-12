from pydantic import BaseModel, field_validator

from typing import Any, Optional, List, Union, Literal, ForwardRef, Dict
import numpy as np 





AttributeTree = ForwardRef('AttributeTree')
    
class AttributeTree(BaseModel):
    """
    Represents a node in a hierarchical tree of attributes and traits used by the frontend
    when inserting genetic and condition applications.
    Each node describes a single attribute or trait and may contain an optional scalar
    value and zero or more child nodes to form a tree. This model is intended to be used
    with Pydantic (BaseModel) and serializes cleanly to/from JSON for API traffic.
    Fields
    - tag (str): A short identifier or name for the attribute or trait (e.g. "att_organ", "att_cellline").
        Should be non-empty.
    - type (Literal["attribute","trait"]): Distinguishes whether the node is an attribute or a trait.
        Within the tree, the type must be alternating along the children (i.e. an attribute node may only
        have trait children, and a trait node may only have attribute children).
    - value (float | int | str | None): Optional scalar value associated with this node. Use None
        when no value is applicable. Numeric values are typical for magnitudes; strings can be used
        for categorical values. Values can only be assigned to trait nodes.
    - children (Optional[List[AttributeTree]]): Optional list of child AttributeTree nodes. Use None
        or an empty list for leaf nodes.
    Validation and conventions
    - tag should be meaningful to the domain and unique among siblings when necessary.
    - type must be exactly "attribute" or "trait".
    - If children is provided, each child must itself be a valid AttributeTree instance.
    - Prefer numeric types for quantitative attributes; use strings for descriptive values.
    Example (Pydantic)
    >>> # Construct a small tree representing a genetic attribute with traits
    >>> root = AttributeTree(
    ...     tag="growth_rate",
    ...     type="attribute",
    ...     value=None,
    ...     children=[
    ...         AttributeTree(tag="baseline", type="trait", value=1.0),
    ...         AttributeTree(tag="temperature_modifier", type="trait", value=0.2)
    ...     ]
    ... )
    >>> # Serialize to dict / JSON for sending to frontend
    >>> root.dict()
    {
            "tag": "growth_rate",
            "type": "attribute",
            "value": 1.2,
            "children": [
                    {"tag": "baseline", "type": "trait", "value": 1.0, "children": None},
                    {"tag": "temperature_modifier", "type": "trait", "value": 0.2, "children": None}
            ]
    }
    """
   
    tag : str # Attribute or Trait String
    type :  Literal["attribute","trait"]
    value : float|int|str = None
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
    AttributeModel
    --------------

    Pydantic model describing an attribute and its behaviour within the system.
    Extends AttributeBaseModel.

    Fields
    - group_tag (str)           : Tag used to group attributes for UI/filtering.
    - s (Optional[str])         : Lowercased search string built from searchable fields.
    - children (Optional[List[str]]):
                                    List of child attribute tags (e.g. unit attributes required
                                    when this attribute allows user input).
    - allow_input (bool)        : If True the user may provide a value for this attribute.
    - has_features_value (Optional[bool]):
                                    If True, attribute values represent selectable features
                                    (for example proteins).
    - has_numeric_input (Optional[bool]):
                                    If True the attribute accepts arbitrary numeric input
                                    (instead of choosing from predefined values).
    - min_state (int)           : Minimal submission state required to define this attribute.
                                    (Defaults to 0.)

    Notes
    - Tag validation is performed by the class-level validator `check_tag` which enforces
        tags to start with "att_".
    - The `s` and `children` fields are normalized by validators to provide consistent
        runtime types (string and list respectively).
    """
    
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



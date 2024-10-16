from typing import List, Dict

from fastapi import APIRouter, Depends, Request, BackgroundTasks
from fastapi.exceptions import HTTPException

from lib.rest.security import rest_verify_user_token, RestSessionInformation

router = APIRouter(prefix="/api/attributes", tags=["Attributes", "Traits"])

# ToDo: Next
# INFO:     127.0.0.1:49582 - "GET /api/users/roles HTTP/1.1" 404 Not Found

@router.post("/q")
def rest_get_attributes(labels : str, count : bool = True, max_attributes : int = 999999):
    pass

@router.get("/attribute_values/q")
def rest_get_attribute_values(labels: str = None, attribute_value_tag: str = None, attribute_tag: str = None,
                              count: bool = True, max_attributes: int = 999999):
    pass

@router.get("/")  # ToDo: Implement PRM
def rest_get_attributes(session: RestSessionInformation = Depends(rest_verify_user_token)):

    # return AttributeResponseModel(attributes=db_attributes.getAttributes().to_dict(orient="records"),
    #                              attribute_values=db_attributes.getAttributeValues().to_dict(orient="records"))
    """
    id : int
    tag : str
    text : str
    priority : int = 500  # attributes will be sorted by priority in descending order
    parent_id : Optional[int] = None  # parent attribute should be Attribute type
    parent_tag : Optional[str] = None  # parent tag
    group_tag : str  # attribute grouping
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

    unit : Optional[Literal["length","concentration","weight","time"]] = None # ToDo: define units like this?
    """

    """
        id : int
    attribute_id : int
    attribute_tag : Optional[str] = None 
    text : str
    tag : str 
    #value : float  # ToDo: str or float or int? or more flexible? :: The excel table says attribute_value, value is not a float then, maybe like
    value : Union[float,str,int] #maybe like this? #changed the excel header attribute_value to value since attribute_id referece to the attribute not the attribute value
    description : Optional[str] = ""
    feature : Optional[str] = None #feature_key 
    """

    return {"attributes": [],  # List[AttributeModel],
            "attribute_values": []}  # List[AttributeValueModel]}
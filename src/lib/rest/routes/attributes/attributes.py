from typing import Any, List, Dict

from fastapi import APIRouter, Depends, Request, BackgroundTasks, status
from fastapi.exceptions import HTTPException

import lib.data as dlib

from lib.rest.security import rest_verify_user_token, RestSessionInformation

router = APIRouter(prefix="/api/attributes", tags=["Attributes", "Traits"])

# ToDo: Next
# INFO:     127.0.0.1:49582 - "GET /api/users/roles HTTP/1.1" 404 Not Found

@router.post("/q")
def rest_get_query_attributes(labels : str, count : bool = True, max_attributes : int = 999999):
    pass

@router.get("/attribute_values/q")
def rest_get_query_traits(labels: str = None, attribute_value_tag: str = None, attribute_tag: str = None,
                              count: bool = True, max_attributes: int = 999999):
    pass

def get_all_attributes() -> (List[Dict[str, Any]], Dict[int, dlib.ABCAttribute]):
    at: dlib.ABCAttribute = dlib.ABCAttribute.get_class()
    attributes: Dict[int, dlib.ABCAttribute] = at.get_all_attributes()

    return ([{"id": obj.get_id(),
              "tag": obj.get_tag(),
              "text": obj.get_text(),
              "priority": obj.get_priority(),
              "parent_id": obj.get_parent_attribute().get_id() if obj.get_parent_attribute() else None,
              "parent_tag": obj.get_parent_attribute().get_tag() if obj.get_parent_attribute() else None,
              "group_tag": None,  # ToDo: Check / Implement grouping of attributes, could be implemented by parent_attributes with high (low numeric) priority
              "mandatory_for_submission": obj.get_required_for_dataset_state() >= dlib.DatasetState.UPLOADED if obj.get_required_for_dataset_state() else False,  # Deprecated, covered by min_state
              "mandatory_for_active": obj.get_required_for_dataset_state() >= dlib.DatasetState.ACTIVE if obj.get_required_for_dataset_state() else False,  # Deprecated, covered by min_state
              "has_features_value": obj.are_trait_values_allowed(),  # Deprecated: replaced with has_trait_values
              "has_numeric_input": obj.are_trait_values_allowed(),  # Deprecated: replaced with has_trait_values, always saves strings
              "has_trait_values": obj.are_trait_values_allowed(),
              "min_state": obj.get_required_for_dataset_state(),
              "allow_as_qc": obj.allowed_for_performance(),
              "allow_as_filter": obj.allowed_as_filter(),
              "allow_for_measurement": obj.allowed_for_samples(),  # Deprecated: replaced with allow_for_samples
              "allow_for_samples": obj.allowed_for_samples(),
              "allow_for_genotype": obj.allowed_for_genotypes(),
              "allow_for_dataset": obj.allowed_for_datasets(),
              "allow_for_user": False,  # Deprecated: User cannot have attributes nor traits
              "unit": None} for db_id, obj in attributes.items()],  # Deprecated unit: not used. unit can be saved as trait: e.g. att_timepoint:h(4) or att_volume:ml(10)
            attributes)

def get_all_traits(attributes: Dict[int, dlib.ABCAttribute] | None = None) -> List[Dict[str, Any]]:
    tr: dlib.ABCTrait = dlib.ABCTrait.get_class()
    traits: Dict[int, dlib.ABCTrait] = tr.get_all_traits(attributes = attributes)

    return [{"id": obj.get_id(),
             "attribute_id": obj.get_attribute().get_id(),
             "attribute_tag": obj.get_attribute().get_tag(),
             "trait_tag": obj.get_tag(),
             "text": obj.get_text(),
             "description": obj.get_description(),
             "tag": obj.get_full_tag(),
             "value": None,  # ToDo: Check implementation of TraitValue and return those here
             "feature": None} for db_id, obj in traits.items()]  # Deprecated, feature will be a normal string value if saved

@router.get("")  # ToDo: Implement PRM
def rest_get_all_attributes(session: RestSessionInformation = Depends(rest_verify_user_token)):

    attribute_list, attribute_dict = get_all_attributes()

    return {"attributes": attribute_list,  # List[AttributeModel],
            "attribute_values": get_all_traits(attributes=attribute_dict),  # Deprecated, use traits instead
            "traits": get_all_traits(attributes=attribute_dict)}  # List[AttributeValueModel]}

import pandas as pd
import time
from typing import Type
import warnings

from fastapi import APIRouter, Depends, HTTPException

import lib.data as dlib
from lib.rest.security import rest_verify_user_token, RestSessionInformation

router = APIRouter(prefix="/api/datasets",tags=["Dataset", "Deprecated"])

def deprecated_api(message):  # ToDo: Replace with from warnings import deprecated; @deprecated with python 3.13
    warnings.warn(message, DeprecationWarning, stacklevel=2)


# parameter endpoints
# response_model=DatasetSubmissionResponseModel,
# tags=["Parameters" ,"Meta data"])
@router.get("/{dataset_label}/meta", deprecated=True)
def get_dataset_params(dataset_label : str,  # deprecated, Todo: /dataset/{label}/meta Is it the same as /datasets/{dataset_label}/ or different?
                       session: RestSessionInformation = Depends(rest_verify_user_token)):  # ToDo: Implement PRM
    ds: dlib.ABCDataset = dlib.ABCDataset.get_class()
    dataset = ds.objectify_with_label(label=dataset_label)

    tv: Type[dlib.ABCTraitValue] = dlib.ABCTraitValue.get_class()

    try:
        traits = {tag: {"id": obj.get_trait().get_id(),  # obj.get_attribute().get_id(),
                        "attribute": obj.get_trait().get_attribute().get_tag(),
                        "trait": obj.get_trait().get_tag(),
                        "full_tag": obj.get_trait().get_full_tag(),
                        "keyword": obj.get_trait().get_keyword(),
                        "text": obj.get_trait().get_tag(),
                        "description": obj.get_trait().get_description(),
                        "value": obj.get_value(),
                        "unit": obj.get_unit(),  # deprecated, could be saved as att_timepoint:hours(5)
                        } for tag, obj in tv.objectify_with_dataset_id(db_id = dataset.get_internal_id())}  # Fixme: can through exception... if nothing is there... none would be more handy here xD
                        # } for tag, trait in dataset.get_traits().items()},  # Fixme: should be trait values, ABCDataset is not designed properly yet
    except dlib.ABCAttributeError as err:
        traits = {}

    samples_attributes = {"str": {"str": [0,1,2,3,4]}}  # ToDo: Dict[str,Dict[str,List[int]]]  # How is it filled exactly?
    samples_attributes_by_sample = {"str":
                                    {"str": [{"id": 0,  # deprecated, use trait id, not clear what id it is
                                              "trait_id": 0,
                                              "trait_tag": "str",
                                              "attribute_id": 0,
                                              "attribute_tag": "str",
                                              "tag": "str",  # full tag
                                              "text": "str",
                                              "description": "",
                                              "value": "str",
                                              "feature": "value",
                                              "key": "value",   # deprecated, query it separately
                                              # "tag": None,  # deprecated, tag of feature? conflict with tag of trait
                                              "genes": None,   # deprecated, query it separately
                                              "proteins": None,   # deprecated, query it separately
                                              "organism": None,  # deprecated, query it separately
                                              "aa_length": 0,  # deprecated, query it separately
                                              "reviewed": False   # deprecated, query it separately
                                              }]
                                     }
                                    }  # ToDo: Dict[str, Dict[str,List[Union[AttributeValueModel,FeatureModel]]]]  # ToDo: Mach hier weiter!


    # "trait_tags": [tag for tag, trait in
    #                dataset.get_attributes().items()] if dataset.get_attributes() else [],  # Question, get all trait_tags? includign samples?
    # "traits": traits,

    data = dataset.get_data()

    timeline = []

    return {"id": dataset.get_internal_id(),
            "label": dataset.get_external_id(),
            "created_on" : time.mktime(dataset.get_created_on_date().timetuple()) if dataset.get_created_on_date() else None,
            "modified_on" : None,  # deprecated (via timeline?)
            "state": dataset.get_state(),  # ToDo: check SubmissionStates in old code
            "title": dataset.get_title(),
            "user_label": dataset.get_owner().get_username(),  # deprecated, use owner_id and owner_username
            "owner_id": dataset.get_owner().get_id(),
            "owner_username": dataset.get_owner().get_username(),
            "contact_email": dataset.get_email(),
            "collaborators": [],  # List[str]  # ToDo: Check
            "project_id": dataset.get_parent_project().get_id() if dataset.get_parent_project() else None,        # Todo: implement project rest api first
            "instrument_id": dataset.get_instrument().get_id() if dataset.get_instrument() else None,  # Todo: implement instrument rest api first
            "metatext": {m.get_tag(): m.get_text() for tag, m in dataset.get_metatexts().items()} if dataset.get_metatexts() else {},  # Dict[str,str]  # Question is this actually used? found separated request to /api/datasets/{label}/meta
            "links" : [url.get_url() for url in dataset.get_urls()] if dataset.get_urls() else [],  # deprecated, use url instead
            "urls": [url.get_url() for url in dataset.get_urls()] if dataset.get_urls() else [],
            "timeline": {},  # TimeLineModel = Field(...,default_factory=TimeLineModel),
            "runlist": None,  # Question, what is a RunListModel? Optional[RunListModel]
            "attributes": {},  # Dict[str,AttributeModel] #The attributes by tags
            "attribute_values_by_tag": {},  # Dict[str,Union[AttributeValueModel,FeatureModel]]
            "dataset_attributes": {},  # Dict[str,List[Union[AttributeValueModel,FeatureModel]]]

            "sample_names": data.get_data_column_names() if dataset.get_data() else [],
            "n_samples": len(data.get_data_column_names()) if data else 0,

            "samples_attributes": {},  # Dict[str,Dict[str,List[int]]],
            "samples_attributes_by_sample": {},  # Dict[str, Dict[str,List[Union[AttributeValueModel,FeatureModel]]]]
            "samples_genotypes": {},  # Dict[str,List[int]] # ToDO: Dict[str,List[int]] = Field(.s..,default_factory=dict)
            "replicates": [],  # ToDo List[int],
            "batches": data.get_samples_batches() if data and data.get_samples_batches() else {},  # Dict[str, str]  # Question: move to samples?
            "genotypes": {}  # ToDo: implement Genotypes and add Dict[str, GenotypeModel]
            }


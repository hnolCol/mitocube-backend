from typing import List, Annotated, Literal, Dict
import time
import warnings

import lib.data as dlib

from lib.rest.security import rest_verify_user_token, RestSessionInformation

from fastapi import APIRouter, Depends, Request, BackgroundTasks
from fastapi.exceptions import HTTPException

router = APIRouter(prefix="/api/dataset", tags=["Datasets", "Timelines"])

def get_dataset(dataset: dlib.ABCDataset):  # ToDo: create PRM
    return {"id": dataset.get_internal_id(),
            "label": dataset.get_external_id(),
            "title": dataset.get_title(),
            "owner_id": dataset.get_owner().get_id(),
            "owner_username": dataset.get_owner().get_username(),
            "contact_email": dataset.get_email(),
            "project_id": dataset.get_parent_project().get_id() if dataset.get_parent_project() else None,  # Todo: implement project rest api first
            "instrument_id": dataset.get_instrument().get_id() if dataset.get_instrument() else None,  # Todo: implement instrument rest api first
            "created_on": time.mktime(dataset.get_created_on_date().timetuple()),
            "uploaded_on": time.mktime(dataset.get_uploaded_on_date().timetuple()),
            "genotypes": [],  # ToDo: implement Genotypes and add Dict[str, GenotypeModel]
            "state": dataset.get_state(),  # ToDo: check SubmissionStates in old code
            "metatext": {m.get_tag(): m.get_text() for m in dataset.get_metatexts()} if dataset.get_metatexts() else {},  # Dict[str,str]
            "urls": [url.get_url() for url in dataset.get_urls()] if dataset.get_urls() else [],
            "runlist": None,  # Question, what is a RunListModel? Optional[RunListModel]
            "trait_tags": [tag for tag, trait in dataset.get_attributes().items()] if dataset.get_attributes() else [],  # Question, get all trait_tags? includign samples?
            "traits": get_dataset_traits(dataset),
            "n_samples" : len(dataset.get_data().get_data_column_names()),
            "sample_names": dataset.get_data().get_data_column_names(),
            "replicates" : dataset.get_data().get_samples_replicates() if dataset.get_data().get_samples_replicates() else {},  # Dict[str, str]  # Question: move to samples?
            "batches": dataset.get_data().get_samples_batches() if dataset.get_data().get_samples_batches() else {},  # Dict[str, str]  # Question: move to samples?
                        # samples_attributes : Dict[str,Dict[str,List[int]]]  # Question, dublicate defition?  # ToDo: Mach hier weiter!
                        # # samples_attributes : Dict[str,SampleAttributesResponse]  # Question, dublicate defition?  # ToDo: Mach hier weiter!
                        # samples_attributes: Dict[str, SampleAttributesResponse]  # Question, dublicate defition?  # ToDo: Mach hier weiter!
                        # samples_attributes_by_sample : Dict[str, Dict[str,List[Union[AttributeValueModel,FeatureModel]]]]  # ToDo: Mach hier weiter!
                        # samples_genotypes : Dict[str,List[int]] = Field(...,default_factory=dict)  # ToDo: Mach hier weiter!
            }  # ToDo: Mach hier weiter!

@router.get("/{label}")  # , response_model=xxx)
def rest_get_dataset(label: str,
                     session: RestSessionInformation = Depends(rest_verify_user_token)):  # ToDo: create PRM
    ds: dlib.ABCDataset = dlib.ABCDataset.get_class()
    return get_dataset(ds.objectify_with_label(label=label))

@router.get("/{label}/timeline")  # , response_model=xxx)
def rest_get_dataset_timeline(label: str,
                              session: RestSessionInformation = Depends(rest_verify_user_token)):  # ToDo: create PRM
    tl: dlib.ABCTimeline = dlib.ABCTimeline.get_class()
    timeline: List[dlib.ABCDatasetTimelineEvent] = tl.objectify_with_dataset_label(dataset_label = label)

    return [{"id": item.get_id(),
             "dataset_label": label,
             "event_on": time.mktime(item.get_timestamp().timetuple()),
             "user_id": item.get_user().get_id(),
             "username": item.get_user().get_username(),
             "state": item.get_state(),
             "type": item.get_type(),
             "comment": item.get_text()} for item in timeline]

def get_dataset_traits(dataset: dlib.ABCDataset):  # ToDo: create PRM
    return {tag: {"id": trait.get_id(),
                  "attribute": trait.get_attribute().get_tag(),
                  "trait": trait.get_tag(),
                  "full_tag": trait.get_full_tag(),
                  "keyword": trait.get_keyword(),
                  "text": trait.get_tag(),
                  "description": trait.get_description()} for tag, trait in dataset.get_traits().items()}

@router.get("/{label}/traits")  # , response_model=xxx)  # ToDo: rewrite to ABCDataSetValues
def rest_get_dataset_traits(label: str,
                            session: RestSessionInformation = Depends(rest_verify_user_token)):  # ToDo: create PRM
    ds: dlib.ABCDataset = dlib.ABCDataset.get_class()
    return get_dataset_traits(dataset = ds.objectify_with_label(label=label))

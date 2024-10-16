from typing import List, Annotated, Literal, Dict
import time
import warnings

import lib.data as dlib

from lib.rest.security import rest_verify_user_token, RestSessionInformation

from fastapi import APIRouter, Depends, Request, BackgroundTasks
from fastapi.exceptions import HTTPException

router = APIRouter(prefix="/api/submissions", tags=["Datasets"])


# ToDo: Implement Routines
# @router.get("/submission/id",
# @router.patch("/submissions/{submission_label}/metatext", summary="Update the metatext of a submission.")
# @router.get("/submissions/metatext", summary="Returns the metatext information that can be used to describe a submission.", response_model=MetaTextSubmissionResponse)
# @router.get("/submissions/states", summary="Returns the states enum as well as colors associated with the state.")
# @router.post("/submissions/{submission_label}/collaborators")
# @router.get("/submissions/{submission_label}/owner", response_model=PublicUser)
# @router.post("/submissions/{submission_label}/owner")
# @router.get("/submissions/count", response_model=Dict[str|int,SubmissionCountResponse])
# @router.get("/submissions/users", response_model=List)
# @router.post("/submissions",summary="Add submission to the database")
# @router.patch("/submissions/{submission_label}/datasetattributes", summary = "Updates a submissions dataset attributes along with an optional change of state.")
# @router.patch("/submissions/{label}/sampleattributes")
# @router.get("/submissions", response_model=List[DatasetSubmissionResponseModel])
# @router.post("/submissions/{submission_label}/runlist", response_model=RunListResponseModel, tags = ["Runlist"])
# @router.get("/submissions/{submission_label}/runlist", response_model=RunListResponseModel, tags = ["Runlist"])

def deprecated_api(message):  # ToDo: Replace with from warnings import deprecated; @deprecated with python 3.13
    warnings.warn(message, DeprecationWarning, stacklevel=2)


@router.get("/q")  # response_model=SubmissionQueryResponse) # Deprecated /submissions/q
def rest_get_query_datasets(state: int | None = None,
                            query: str | None = None,  # query : Annotated[str | None, Query(min_length=1)] = None,
                            feature_key: str | None = None,
                            attribute_value_tag: str | None = None,
                            attribute_tag: str | None = None,  # Question: What does that mean exactly? just anything with att_soemthing?
                            genotype_label: str | None = None,
                            user_label: str | None = None,
                            max_submissions: int | None = 50,
                            join: Literal["inner","outer"] = "inner",  # Question: What does that mean?
                            session: RestSessionInformation = Depends(rest_verify_user_token)):

    deprecated_api("/api/submissions/q is deprecated, use /api/datasets/q instead")

    db: dlib.ABCDatabase = dlib.ABCDatabase.get_class()
    ds: dlib.ABCDataset = dlib.ABCDataset.get_class()

    dataset_ids, dataset_labels = db.query_datasets_ids(query = query,
                                                        states = [state] if state else None,
                                                        feature_keys = [feature_key] if feature_key else None,
                                                        trait_tags = [attribute_value_tag] if attribute_value_tag else None,
                                                        trait_ids = None,
                                                        genotype_labels = [genotype_label] if genotype_label else None,
                                                        usernames = [user_label] if user_label else None,
                                                        limit_to_n = max_submissions,
                                                        limit_offset = 0)

    submissions = []

    for ix in range(len(dataset_ids)):
        dataset: dlib.ABCDataset = ds.objectify_with_id(db_id=dataset_ids[ix])

        tl: dlib.ABCTimeline = dlib.ABCTimeline.get_class()
        timeline: List[dlib.ABCDatasetTimelineEvent] = tl.objectify_with_dataset_id(dataset_id=dataset_ids[ix])

        timeline_migrated = {"created_on": time.mktime(dataset.get_created_on_date().timetuple()),  # Question: Dataset created or timeline?
                             "modified_on": time.mktime(timeline[0].get_timestamp().timetuple()),  # deprecated, should be first entry in entries
                             "label": dataset_labels[ix],
                             "entries": [{"id": item.get_id(),
                                          "label": str(item.get_id()),  # Question: id? does not exist
                                          "created_on": time.mktime(item.get_timestamp().timetuple()),
                                          "user_label": str(item.get_user().get_username()),  # deprecated, changed to username
                                          "user_id": str(item.get_user().get_id()),
                                          "username": str(item.get_user().get_username()),
                                          "state": item.get_state(),
                                          "type": item.get_type(),
                                          "comment": item.get_text()} for item in timeline]}

        submissions.append({"id": dataset_ids[ix],
                            "label": dataset_labels[ix],
                            "title": dataset.get_title(),
                            "user_id": dataset.get_owner().get_id(),
                            "username": dataset.get_owner().get_username(),
                            "user_label": dataset.get_owner().get_username(),  # deprecated, changed to username
                            "collaborators": [],  # ToDo: collaborators List[str]
                            "created_on": time.mktime(dataset.get_created_on_date().timetuple()),
                            "uploaded_on": None,  # time.mktime(dataset.get_uploaded_on_date().timetuple()),  # ToDo: Check if uploaded on is required (should be covered by time line, see ABCDataset)
                            "modified_on": time.mktime(timeline[0].get_timestamp().timetuple()),  # deprecated, should be first entry in entries
                            "genotypes": [],  # ToDo: implement Genotypes and add Dict[str, GenotypeModel]
                            "state": dataset.get_state(),  # ToDo: check SubmissionStates in old code
                            "metatext" : {m.get_tag(): m.get_text() for m in dataset.get_metatexts()} if dataset.get_metatexts() else None,  # Dict[str,str]
                            "links": [{"id": -1, "url": url.get_url(), "comment": None} for url in dataset.get_urls()] if dataset.get_urls() else None,  # deprecated, changed to url, id and comment not required
                            "urls": [url.get_url() for url in dataset.get_urls()] if dataset.get_urls() else None,
                            "runlist": None,  # Question, what is a RunListModel? Optional[RunListModel]
                            "timeline": timeline_migrated,  # deprecated, query via future /api/dataset/{}/timeline # ToDo: Implement /api/dataset/{}/timeline
                            "attributes": {},  # Dict[str,AttributeModel] # Question, what is it for?  # ToDo: Mach hier weiter!
                            "dataset_attributes": {},  # Dict[str,List[Union[AttributeValueModel, FeatureModel]]]  # Question, what is it for? difference to the above?  # ToDo: Mach hier weiter!
                            "attribute_values_by_tag": {},  # Dict[str,Union[AttributeValueModel,FeatureModel]]  # Question, what is it for?  # ToDo: Mach hier weiter!
                            "n_samples": len(dataset.get_data().get_data_column_names()),
                            "sample_names": dataset.get_data().get_data_column_names(),
                            "replicates": [],  # List[int]  # ToDo: Mach hier weiter!
                            "samples_attributes": {},  # Dict[str,Dict[str,List[int]]]  # ToDo: Mach hier weiter!
                            "samples_attributes_by_sample":  {},  # Dict[str, Dict[str,List[Union[AttributeValueModel,FeatureModel]]]]  # ToDo: Mach hier weiter!
                            "samples_genotypes": {}  # Dict[str,List[int]]  # ToDo: Implement after implementing Genotypes
                            })

    # was SubmissionQueryResponse # ToDo: Implement PRM
    return {"submissions": submissions,  # Question: What is in the list? Dict? was metadata, was List[DatasetSubmissionResponseModel]
            "ids": dataset_ids,  # dataset ids, List[int]
            "labels": dataset_labels,  # dataset labels, List[str]
            "query_count": 0,  # query_match_count,
            "total_count": 0}  # Question: what is the different between query count and total count? total datasets between selected?


@router.get("/states", summary="Returns the states enum as well as colors associated with the state.")
def get_project_states(session: RestSessionInformation = Depends(rest_verify_user_token)):  # ToDo: Implement PRM
    deprecated_api("/api/submissions/states is deprecated, use /api/datasets/states instead")  # ToDo: Implement  /api/datasets/states
    dlib.DatasetState

    # ToDo: Currently manualy, make int configurable and implement it automattically from an enum (different enum type or with own static functions?)

    return {"states": {"INACTIVE": -50, "CANCELED": -20, "PAUSED": -10,
                       "INITIALISED": 0, "PROCESSED": 10, "MEASURING": 20, "UPLOADED": 25,
                       "ANALYSIS": 30, "DONE": 40, "ACTIVE": 50},  # Dict[str,int] = get_enum_as_dict(SubmissionStates)
            "states_inv": {-50: "INACTIVE", -20: "CANCELED", -10: "PAUSED",
                           0: "INITIALISED", 10: "PROCESSED", 20: "MEASURING", 25: "UPLOADED",
                           30: "ANALYSIS", 40: "DONE", 50: "ACTIVE"},  # Dict[int,str] = get_inversed_enum_as_dict(SubmissionStates)  # Question, what is it vor?
            "colors": {"INACTIVE": "#C7253E", "CANCELED": "#821131", "PAUSED": "#B7B7B7",
                       "INITIALISED": "#A3D8FF", "PROCESSED": "#FFFF80", "MEASURING": "#F9E400", "UPLOADED": "#FFAF00",
                       "ANALYSIS": "#640D5F", "DONE": "#091057", "ACTIVE": "#024CAA"},  # Dict[str,str] = get_enum_as_dict(SubmissionStateColors)
            "colors_inv": {-50: "#C7253E", -20: "#821131", -10: "#B7B7B7",
                           0: "#A3D8FF", 10: "#FFFF80", 20: "#F9E400", 25: "#FFAF00",
                           30: "#640D5F", 40: "#091057", 50: "#024CAA"}}  # Dict[int,str] = get_enum_as_dict(SubmissionStateColors,SubmissionStates)}
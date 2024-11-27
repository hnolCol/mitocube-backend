from typing import List, Annotated, Literal, Dict
import warnings

import lib.data as dlib

from lib.rest.security import RestPermissionSteward, RestSessionInformation

from fastapi import APIRouter, Depends, Request, BackgroundTasks, status
from fastapi.exceptions import HTTPException

router = APIRouter(prefix="/api/datasets", tags=["Datasets"])

@router.get("/q")  # response_model=SubmissionQueryResponse)
def rest_get_query_datasets(states: List[int] | None = None,  # Question, is list possible here?
                            query: str | None = None,
                            features: List[str] | None = None,  # Question, is list possible here?
                            traits: List[str] | None = None,  # Question, is list possible here?
                            trait_ids: List[int] | None = None,  # Question, is list possible here?
                            genotypes: List[str] | None = None,  # Question, is list possible here?
                            usernames: List[str] | None = None,  # Question, is list possible here?
                            n: int | None = 50,
                            n_offset: int | None = 0,
                            session: RestSessionInformation = Depends(RestPermissionSteward())):

    raise Exception("Is this called?")
    #
    if len(query) < 3:
        # Throw Exception to prevent unnecessary long runtime, e.g. query = "a" would return several hundred or thousands of features anyway
        raise HTTPException(status_code = status.HTTP_400_BAD_REQUEST,  # ToDo: Collect to central spot / library
                            detail = "The query string `{}` is too short. 2 characters required at least".format(query),
                            headers = {"WWW-Authenticate": "Bearer"})

    db: dlib.ABCDatabase = dlib.ABCDatabase.get_class()
    dataset_ids, dataset_labels = db.query_datasets_ids(query = query,
                                                        states = states,
                                                        feature_keys = features,
                                                        trait_tags = traits,
                                                        trait_ids = trait_ids,
                                                        genotype_labels = genotypes,
                                                        usernames = usernames,
                                                        limit_to_n = n,
                                                        limit_offset = n_offset if n else 0)

    # SubmissionQueryResponse # ToDo: Implement PRM
    return {"submissions": [],  # Question: What is in the list? Dict? was metadata,
            "labels": [],  # labels,
            "query_count": 0,  # query_match_count,
            "total_count": 0}  # ToDo: Mach hier weiter!

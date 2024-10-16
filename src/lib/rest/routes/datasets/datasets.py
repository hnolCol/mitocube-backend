from typing import List, Annotated, Literal, Dict
import warnings

import lib.data as dlib

from lib.rest.security import rest_verify_user_token, RestSessionInformation

from fastapi import APIRouter, Depends, Request, BackgroundTasks
from fastapi.exceptions import HTTPException

router = APIRouter(prefix="/api/datasets", tags=["Datasets"])

@router.get("/q")  # response_model=SubmissionQueryResponse)
def rest_get_query_datasets(states: List[int] | None = None,
                            query: str | None = None,
                            features: List[str] | None = None,
                            traits: List[str] | None = None,
                            trait_ids: List[int] | None = None,
                            genotypes: List[str] | None = None,
                            usernames: List[str] | None = None,
                            n: int | None = 50,
                            n_offset: int | None = 0,
                            session: RestSessionInformation = Depends(rest_verify_user_token)):

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

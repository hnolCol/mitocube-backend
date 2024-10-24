from typing import Dict, List

import lib.data.sql.postgresql as psql

from fastapi import APIRouter, Depends, HTTPException

from lib.rest.security import rest_verify_user_token, RestSessionInformation


router = APIRouter(prefix="/api/features",
                   tags=["Features"])


@router.get("")
def rest_get_query_features(query: str,
                            proteome_ids: str | None = None,
                            max_features: int = 30,
                            session: RestSessionInformation = Depends(rest_verify_user_token)):  # Todo: create PRM

    db_features = psql.PostgreSQLFeatureDatabase()  # Todo make, more general query / request

    if proteome_ids and proteome_ids == "":
        proteome_ids = None

    features = db_features.search_features(search_term = query)  # ToDo: make a better function that maybe returns a Dict

    # ToDo: Filter results (proteome_ids, add species?) --> compare it with the respectie DB features query function
    if proteome_ids and proteome_ids != "":
        features = features[features.index.isin([proteome_ids], level=0)]

    if max_features < 1:  # Question, should it limited with min and max value?
        max_features = 1
    elif max_features > 1000:
        max_features = 1000

    if features.shape[0] > max_features:
        features = features[:max_features]

    return [{"key": row["key"],
             "entry": row["entry"],
             "tag": row["entry"],  # Question, was is within tag?
             "genes": row["genes"],
             "proteins": row["proteins"],
             "proteom_id": row["proteom_id"],
             "organism": row["organism"],
             "organism_id": row["organism_id"],
             "aa_length": row["aa_length"],
             "mass": row["mass"],
             "reviewed": True} for ix, row in features.iterrows()]  # Question, what does reviewed mean?






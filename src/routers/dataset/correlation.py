from fastapi import APIRouter, Depends, HTTPException
from lib.database.Database import get_db
from lib.database.abstract.Database import DatabaseABC
import pandas as pd 
import numpy as np 
from typing import List, Dict, Literal
from config.models.user import UserModel



from config.exceptions.HTTPExceptions import no_data_found_http_exception

from services.users import get_user_from_token
from services.submission import check_submission_access



router = APIRouter(dependencies=[Depends(get_user_from_token)],
    prefix="/api/datasets",
    tags=["Dataset","Submission","Correlation"]
    )



@router.get("/{submission_tag}/correlation/{feature_tag}")
def get_correlation(submission_tag : str,
                    feature_tag : str, 
                    annotation_tag : str = None, 
                    direction : Literal["positive","negative","both"] = "both", 
                    r_threshold : float = 0.6,
                    limit : int = 40, 
                    min_data_points : int = 5,
                    user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)):
    "Returns the correlated features within the given submission tag."
    
    check_submission_access(submission_tag = submission_tag, user = user, db = db)
    if not db.submission_has_dataset(tag = submission_tag): no_data_found_http_exception 
    if annotation_tag is not None:
        if not db.annotations.exists(tag = annotation_tag): raise HTTPException(status_code=404, detail=f"Annotation tag {annotation_tag} not found.")
    correlated_features = db.features.get_correlated_features(tag= feature_tag,
                                           annotation_tag = filter_tag,
                                           submission_tags = [submission_tag],
                                           direction = direction,
                                           limit = limit,
                                           min_data_points = min_data_points)
    
    boolIdx = np.abs(correlated_features.loc[:,"pearson"]) > r_threshold
    return correlated_features.loc[boolIdx].to_dict(orient="records")
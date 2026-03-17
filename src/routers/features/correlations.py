from fastapi import APIRouter, Depends, HTTPException
from typing import List, Literal
from config.models.user import UserModel
from services.users import get_user_from_token
from config.models.parameter import APIParamString

from lib.database.Database import Database

from services.statistics.t import t_to_p
DB = Database.DB()


router = APIRouter(
    prefix="/api/features",
    tags=["Proteins","Correlations"]
    )
@router.get("/{tag}/correlations")
def get_protein_correlations(tag: str, annotation_tags : str = None, min_data_points : int = 2, limit : int = None, direction : Literal["both", "positive", "negative"] = "both", user: UserModel = Depends(get_user_from_token)):
    """
    Returns the correlation of a given protein tag with all other proteins across all samples. 
    The correlation is computed using Pearson correlation and includes the p-value for the correlation.
    """
    
    if DB.features.exists(tag=tag) is False:
        raise HTTPException(status_code=404, detail="Feature not found") 

    if annotation_tags is not None:
        annotation_tags = APIParamString(param=annotation_tags).param
        print(annotation_tags,"IN TAGS!")
        for annotation_tag in annotation_tags:
            if DB.annotations.exists(tag=annotation_tag) is False:
                raise HTTPException(status_code=404, detail=f"Annotation {annotation_tag} not found")
    
    if min_data_points < 2:
        raise HTTPException(status_code=400, detail="min_data_points must be at least 2")
    
    if min_data_points > DB.samples.count(has_protein_quantification=True):
        raise HTTPException(status_code=400, detail=f"min_data_points cannot be greater than the number of samples with protein quantification ({DB.samples.count(has_protein_quantification=True)})")
    r = DB.features.get_correlated_features(tag = tag, annotation_tags=annotation_tags, direction=direction, min_data_points=min_data_points, limit=limit)
    r["index"] = range(len(r.index))
    #add p-values
    r["p-value"] = t_to_p(ts=r["t"].values, ns = r["N"].values)
    
    return r.to_dict(orient="records")
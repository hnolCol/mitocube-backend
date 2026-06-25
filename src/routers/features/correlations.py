from fastapi import APIRouter, Depends, HTTPException
from typing import List, Literal
from config.models.user import UserModel
from services.users import get_user_from_token
from config.models.parameter import APIParamString

from lib.database.Database import Database

from services.statistics.t import t_to_p
from scipy.stats import false_discovery_control

DB = Database.DB()


router = APIRouter(
    prefix="/api/features",
    tags=["Proteins","Correlations"]
    )
@router.get("/{tag}/correlations") 
def get_protein_correlations(tag: str, 
                             metrics : Literal["raw", "z_score_sample","z_score_protein_group", "log2_fc_vs_mean"] = "raw",
                             annotation_tags : str = None, 
                             min_data_points : int = 2, 
                             limit : int = None, 
                             direction : Literal["both", "positive", "negative"] = "both", 
                             fdr : float = 0.05, 
                             ca_tags : str = None,
                             user: UserModel = Depends(get_user_from_token))-> List[dict]:
    """
    Returns the correlation of a given protein tag with all other proteins across all samples. 
    The correlation is computed using Pearson correlation and includes the p-value for the correlation.
    """
    
    if DB.features.exists(tag=tag) is False:
        raise HTTPException(status_code=404, detail="Feature not found") 

    if annotation_tags is not None:
        annotation_tags = APIParamString(param=annotation_tags).param
        for annotation_tag in annotation_tags:
            if DB.annotations.exists(tag=annotation_tag) is False:
                raise HTTPException(status_code=404, detail=f"Annotation {annotation_tag} not found")
    
    if min_data_points < 2:
        raise HTTPException(status_code=400, detail="min_data_points must be at least 2")
    
    if min_data_points > DB.samples.count(has_protein_quantification=True):
        raise HTTPException(status_code=400, detail=f"min_data_points cannot be greater than the number of samples with protein quantification ({DB.samples.count(has_protein_quantification=True)})")
    
    submission_tags = DB.submission_filter.find(protein_tags=[tag], ca_tags=APIParamString(param=ca_tags).param if ca_tags is not None else None)
    if submission_tags is not None and len(submission_tags) == 0:
        return []

    r = DB.features.get_correlated_features(tag = tag, metrics = metrics, submission_tags=submission_tags, annotation_tags=annotation_tags, direction=direction, min_data_points=min_data_points, limit=limit)
    r["index"] = range(len(r.index))
    r = r.dropna(subset=["t","N"])
    if r.empty:
        return []
    #add p-values
    #subsetting and calculating FDR
    r["p-value"] = t_to_p(ts=r["t"].astype(float).values, ns = r["N"].astype(float).values)
    r.loc[:,"fdr"] = false_discovery_control(r["p-value"].values)
    r = r.loc[r["fdr"] < fdr,:]

    return r.to_dict(orient="records")
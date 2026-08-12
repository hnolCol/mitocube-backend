from fastapi import APIRouter, Depends, HTTPException
from typing import List, Literal
import pandas as pd 
from typing import Dict 
from config.models.user import UserModel
from config.models.feature import FeatureSequenceResponseModel
from config.models.annotations.feature import FeatureDataResponseModel, FeatureNeoModel
from config.enums.states import SubmissionStatesEnums
from services.users import get_user_from_token
from config.models.parameter import APIParamString
from config.models.calculations.quantile import QuantileModel 

from lib.database.Database import Database

from config.exceptions.HTTPExceptions import protein_not_found
from collections import OrderedDict
DB = Database.DB()


router = APIRouter(
    prefix="/api/features",
    tags=["Features"]
    )


@router.get("/q")
def find_feature_by_query(search_string : str = None, submission_tag : str = None, include_types : str = None, exclude_types : str = None, limit : int = 30, sort_by_stat : str = None, annotation_tags : str = None, user : UserModel = Depends(get_user_from_token)):

    include_types = APIParamString(param=include_types).param
    exclude_types = APIParamString(param=exclude_types).param
    annotation_tags = APIParamString(param=annotation_tags).param

    
    if submission_tag is not None:
        if not DB.submissions.exists(tag=submission_tag):
            raise HTTPException(status_code=404, detail=f"Submission {submission_tag} not found")
        if not DB.submission_filter.has_user_access(user_tag=user.tag, submission_tag=submission_tag):
            raise HTTPException(status_code=403, detail=f"User {user.tag} does not have access to submission {submission_tag}")
    
    if include_types is not None:
        if any([t not in ["protein_groups","peptides"] for t in include_types]):
            raise HTTPException(status_code=400, detail="include_types must be one of 'protein_groups', 'peptides'.")
    if exclude_types is not None:
        if any([t not in ["protein_groups","peptides"] for t in exclude_types]):
            raise HTTPException(status_code=400, detail="exclude_types must be one of 'protein_groups', 'peptides'.")
        
    if include_types is not None and exclude_types is not None:
        if any([t in exclude_types for t in include_types]):
            raise HTTPException(status_code=400, detail="include_types and exclude_types must not contain the same types.")
    
    if (include_types is None and exclude_types is None) or (len(include_types) == 0 and len(exclude_types) == 0):
        include_types = ["protein_groups","peptides"]
        
    pgs = []
    peptides = []
    pg_peptides = {}
    if "protein_groups" in include_types:
        pgs_search_result = DB.protein_groups.find(search_string=search_string, limit=limit, submission_tag=submission_tag, sort_by_stat_attribute=sort_by_stat, annotation_tags=annotation_tags)
    else:
        pgs_search_result = []
    
    if "peptides" in include_types:
        
        peptides = DB.peptides.find(search_string=search_string, limit=limit, provide_protein_info=True, submission_tag=submission_tag)
        
        for peptide, pgs in peptides:
            for pg in pgs:
                if pg not in pg_peptides:
                    pg_peptides[pg] = []
                pg_peptides[pg].append(peptide)
                
    peptide_only_matches_pgs = [pg for pg in pg_peptides if pg not in pgs_search_result]
    pgs_with_peptides = [{"tag" : pg, "pg_match" : True,  "protein_tags" : pg.split(";"), "peptide_match" : pg in pg_peptides, "peptide_tags" : pg_peptides[pg] if pg in pg_peptides else []} for pg in pgs_search_result]
    peptide_only = [{"tag" : pg, "pg_match" : False, "protein_tags" : pg.split(";"), "peptide_match" : True, "peptide_tags" : peptides} for pg,peptides in pg_peptides.items() if pg in peptide_only_matches_pgs]


    result = pgs_with_peptides + peptide_only
    return result[:limit]

    
        
@router.get("/{feature_tag}/d")
def get_feature_data(feature_tag : str, submission_tag : str, append_condition_procedure : bool = True, metrics : Literal["raw","z_score_sample","z_score_protein_group","log2_fc_vs_mean"] = "raw", user : UserModel = Depends(get_user_from_token)):
    """Returns the data for a specific feature in a specific submission. This includes the quantification values for the feature in all samples of the submission and, if append_condition_procedure is True, also the condition applications for the samples. 
    This Endpoint combines peptide and protein group features. If you know what type the 
    feature has, you should likely use the more specific endpoints (proteins/{protein_tag}/d). 
    
    API Endpoint
    ------------
    ``GET api/features/{feature_key}/d```
    
    Parameters
    ----------
    feature_key : str
        The key of the feature (UniprotIDs for protein groups
        ) and peptide sequences for peptides .
    user : UserModel
        The user that was identified by the token.
    
    Returns
    -------
    List[Dict]
    
    Raises
    ------
    HTTPException
        If the feature with the given key does not exist.
    
    """
    
    if not DB.features.exists(tag = feature_tag):
        raise HTTPException(status_code=404, detail = "Feature tag not found in the database.")
    if not DB.submissions.exists(tag = submission_tag):
        raise HTTPException(status_code=404, detail = "Submission tag not found in the database.")
    
    if not DB.submission_filter.has_user_access(user_tag = user.tag, submission_tag = submission_tag):
        raise HTTPException(status_code=403, detail = "User does not have access to the submission.")
    
    sample_tags = DB.submissions.get_samples(tag = submission_tag, ignore_excluded=True) # check if submission has samples
    if not sample_tags:
        raise HTTPException(status_code=404, detail = "No samples found for submission tag.")
    d = []
    attribute_tags = set()
    for sample_tag in sample_tags:
        di = {"tag" : sample_tag, "value" : None}
        if not DB.samples.exists(tag = sample_tag):
            continue 
        if DB.samples.is_excluded(tag = sample_tag):
            continue  # Skip excluded samples
        quantified_value = DB.samples.get_quantified_data_for_feature(tag=sample_tag, feature_tag=feature_tag, metrics=metrics)
        di["value"] = quantified_value
        if append_condition_procedure:
            condition_applications = DB.samples.get_condition_applications_by_sample_for_submission(submission_tag=submission_tag, sort_ca_tags=True, return_sample_index=False)  #preload condition applications
            if DB.submissions.has_genotypes(tag = submission_tag):
                genotypes = DB.samples.get_genotypes_by_sample_for_submission(submission_tag=submission_tag, sort_ca_tags=True, return_sample_index=False)  #preload genotypes
                condition_applications = condition_applications.join(genotypes, how="outer")
            for attribute_tag in condition_applications.columns:
                attribute_tags.add(attribute_tag)
                condition_application_tags = condition_applications.loc[sample_tag, attribute_tag]
                di[attribute_tag] = condition_application_tags
                #else:
        d.append(di)

    return {"data" : d, "attribute_tags" : list(attribute_tags), "feature_tag" : feature_tag, "submission_tag" : submission_tag}
    
    

    
@router.get("/{tag_x}/{tag_y}/pairwise_quant")
def get_pairwise_quantification(tag_x : str, tag_y : str, user : UserModel = Depends(get_user_from_token)): 
    "Returns all the quantification values for two features. For example to visualize a correlation."
    tag_not_exists = [tag for tag in [tag_x,tag_y] if not DB.features.exists(tag = tag)] 
    if len(tag_not_exists) > 0:
        raise HTTPException(status_code=404, detail=f"The tag(s) do(es) not exits: {tag_not_exists} in the database.")

    df = DB.features.get_pairwise_feature_quant(feature_tag_x=tag_x, feature_tag_y=tag_y)
                        
    return df.to_dict(orient="records")




@router.get("/{feature_tag}")
def get_feature_by_tag(feature_tag : str, user : UserModel = Depends(get_user_from_token)):
    "" 
    if DB.proteins.exists(tag = feature_tag):
        return DB.proteins.get(tag = feature_tag)
    if DB.protein_groups.exists(tag = feature_tag):
        return DB.protein_groups.get(tag = feature_tag)
    if DB.peptides.exists(tag = feature_tag):
        return DB.peptides.get(tag = feature_tag)
    
    raise HTTPException(status_code=404, detail = "Feature tag not found in the database.")
    

@router.get("/{feature_tag}/i")
def get_feature_info(feature_tag : str, user : UserModel = Depends(get_user_from_token)):
    "" 
    protein = DB.features.get_protein_by_tags(tags = [feature_tag], as_data_frame=False) 
    if len(protein) == 0: raise protein_not_found

    return {
            "i" : protein[0],
            "annotation_tags": []
            }
    

    
    
@router.get("/{feature_tag}/annotations") 
def get_feature_annotations(feature_tag : str, user : UserModel = Depends(get_user_from_token)) -> List[str]:
    
    if DB.proteins.exists(tag = feature_tag):
        p_tags = [feature_tag]
    elif DB.protein_groups.exists(tag = feature_tag):
        p_tags = feature_tag.split(";")
    else:
        raise HTTPException(status_code=404, detail = "Feature tag not found in the database.")
    
    return DB.annotations.find(protein_tags=p_tags, limit = None)
    
    
@router.get("/{feature_tag}/abundance") 
def get_feature_abundance(feature_tag : str, 
                          attribute_tag : str = None,
                          value : Literal["raw","z_score_sample","z_score_protein_group","log2_fc_vs_mean"] = "raw", 
                          user : UserModel = Depends(get_user_from_token)) -> QuantileModel|List[QuantileModel]|Dict[str,QuantileModel]:
    
    return DB.features.get_abundance_distribution(tag = feature_tag, attribute_tag = attribute_tag, value = value)


@router.get("/{feature_tag}/abundance/samples")
def get_feature_sample_abundance(feature_tag : str, metrics : Literal["raw","z_score_sample","z_score_protein_group","log2_fc_vs_mean"] = "raw", user : UserModel = Depends(get_user_from_token)):
    if not DB.features.exists(tag=feature_tag):
        raise HTTPException(status_code=404, detail=f"The feature tag does not exist: {feature_tag} in the database.")
    submission_scope_tags = DB.submission_filter.get_user_submission_scope_tags(user_tag=user.tag)
    if len(submission_scope_tags) == 0:
        raise HTTPException(status_code=404, detail=f"The user {user.tag} does not have any submission scope tags (e.g. no permission to access any submissions).")
    df =  DB.features.get_quantification_per_sample(tag = feature_tag, metrics = metrics, submission_tags = submission_scope_tags)
    if df.empty:
        raise HTTPException(status_code=404, detail=f"No quantification data found for feature tag: {feature_tag} in the database.")
    df.loc[:,"value"] = df["value"].astype(float)
    return df.to_dict(orient="records")


@router.get("/{feature_tag}/quant_count")
def get_quantification_counts(feature_tag : str):
    "Returns the number of samples that quantified the given feature (protein) and the number of samples that used the same proteome."
    if not DB.features.exists(tag = feature_tag): raise HTTPException(status_code=404, detail = "Feature tag not found in the database.")
    proteome_tags = DB.features.get_proteome(tags = [feature_tag])
    counts = DB.features.count_samples_quantifying_protein(tags=[feature_tag])
    if not feature_tag in counts.index:
        raise HTTPException(status_code=404, detail="Counting the samples that quantified the protein resulted in an error." )
    n_samples = DB.samples.count(trait_tag = proteome_tags.loc[feature_tag,"proteome_tag"])
    
    return {"samples" : int(counts.loc[feature_tag,"n_samples"]), "total_samples" : int(n_samples)}


@router.get("/{feature_tag}/variance")
def get_feature_variance(feature_tag : str, submission_tags : str = None, user : UserModel = Depends(get_user_from_token)):
    """_summary_

    Parameters
    ----------
    feature_key : str
        _description_

    Returns
    -------
    _type_
        _description_
    """
    submission_scope_tags = DB.submission_filter.get_user_submission_scope_tags(user_tag = user.tag)
        
    if submission_tags is not None:
        submission_tags = [submission_tag for submission_tag in APIParamString(param=submission_tags).param if submission_tag in submission_scope_tags]
    else:
        submission_tags = submission_scope_tags
    if len(submission_tags) == 0:
        raise HTTPException(status_code=404, detail=f"The user {user.tag} does not have any submission scope tags (e.g. no permission to access any submissions).")
    submission_scope_tags = DB.submission_filter.get_user_submission_scope_tags(user_tag = user.tag)
    f_stats = DB.features.get_f_value(tags=[feature_tag], submission_tags=APIParamString(submission_tags).param)
    return f_stats.to_dict(orient="records")
    


@router.get("/{feature_tag}/sequence",
            summary="Returns the stored sequence in the annotation database.")
def get_feature_sequence(feature_tag : str) -> List[FeatureSequenceResponseModel]: #user : UserModel = Depends(get_user_from_token)
    """
    Returns the sequence for a specific feature_tag (Uniprot ID)
    
    API Endpoint
    ------------
    The API endpoint of this route HTTP method is : 
    ``GET  /api/features/{feature_key}/sequence``
    
    Parameters
    ----------
    feature_tag : str 
        The feature_key to get the sequence from.
    user : UserModel
        The user that was identified by the token.
    
    
    See also
    --------
    Please use the api endpoint /annotations to submit a list of feature_ids to 
    retrieve annotations efficiently. 
    """
    return DB.features.get_protein_sequence(tags = APIParamString(param=feature_tag).param)
    
    
    

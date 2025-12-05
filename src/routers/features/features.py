from fastapi import APIRouter, Depends, HTTPException
from typing import List
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
def find_feature_by_query(search_string : str = None, submission_tag : str = None, include_types : str = None, exclude_types : str = None, limit : int = 30):

    include_types = APIParamString(param=include_types).param
    exclude_types = APIParamString(param=exclude_types).param

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
        
    print(include_types,exclude_types)
    pgs = []
    peptides = []
    pg_peptides = {}
    if "protein_groups" in include_types:
        
        pgs_search_result = DB.protein_groups.find(search_string=search_string, limit=limit, submission_tag=submission_tag)
        print("pgs_search_result ", pgs_search_result)
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
def get_feature_data(feature_tag : str, submission_tag : str, append_condition_procedure : bool = True, user : UserModel = Depends(get_user_from_token)):
    """Returns the data for a specific feature in all datasets it was detected in. 
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
    
    sample_tags = DB.submissions.get_samples(tag = submission_tag) # check if submission has samples
    if not sample_tags:
        raise HTTPException(status_code=404, detail = "No samples found for submission tag.")
    d = []
    attribute_tags = set()
    for sample_tag in sample_tags:
        di = {"tag" : sample_tag, "value" : None}
        if not DB.samples.exists(tag = sample_tag):
            continue 
        quantified_value = DB.samples.get_quantified_data_for_feature(tag=sample_tag, feature_tag=feature_tag)
        di["value"] = quantified_value
        if append_condition_procedure:
            ca_tags = DB.samples.get_condition_applications(tag=sample_tag, group_by_attribute=True)
            
            for ca_tag in ca_tags:
                attribute_tag = ca_tag.get("attribute_tag")
                if attribute_tag is None:   
                    continue
                attribute_tags.add(attribute_tag)
                condition_application_tags = ";".join(ca_tag.get("condition_application_tags", []))
                di[attribute_tag] = condition_application_tags
                #else:
        d.append(di)

    return {"data" : d, "attribute_tags" : list(attribute_tags), "feature_tag" : feature_tag, "submission_tag" : submission_tag}
    
    
    
    
    
# @router.get("")
# def get_features_by_query(query : str, proteome_tags : str = None, limit : int = 30)->List[FeatureNeoModel]:
#     """Finds query by feautre 

#     Parameters
#     ----------
#     query : str
#         The query string 
#     proteome_ids : str, optional
#         The list of proteomes to query the feature in. If None, alle available features will be searched for
#         If multiple proteomes should be provided, separate them by a ';'. 
#     limit : int, optional
#         The maximum number of features to be returned.
#     user : UserModel, optional
#         _description_, by default Depends(get_user_from_token)

#     Returns
#     -------
#     _type_
#         _description_
#     """
#     return DB.features.find(search_string = query, proteome_tags = APIParamString(param=proteome_tags).param, limit = limit)
    

    
@router.get("/pairwise_quant")
def get_pairwise_quantification(feature_tag_x : str, feature_tag_y : str): 
    "Returns all the quantification values for two features. For example to visualize a correlation."
    tag_not_exists = [tag for tag in [feature_tag_x,feature_tag_y] if not DB.features.exists(tag = tag)] 
    if len(tag_not_exists) > 0:
        raise HTTPException(status_code=404, detail=f"The tag(s) do(es) not exits: {tag_not_exists} in the database.")

    df = DB.features.get_pairwise_feature_quant(feature_tag_x=feature_tag_x,
                                           feature_tag_y=feature_tag_y)
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

    # if not DB.features.exists(tag = feature_tag):
    #     raise HTTPException(status_code=404, detail = "Feature tag not found in the database.")
    # feature = DB.features.get_protein_by_tags(tags=[feature_tag], as_data_frame=False)
    # if len(feature) == 1:
    #     return feature[0]
    

@router.get("/{feature_tag}/i")
def get_feature_info(feature_tag : str, user : UserModel = Depends(get_user_from_token)):
    "" 
    protein = DB.features.get_protein_by_tags(tags = [feature_tag], as_data_frame=False) 
    if len(protein) == 0: raise protein_not_found
    filters = DB.filters.get(feature_tag=feature_tag)
    #DB.features.get_quant_stats(tags = [feature_tag])

    return {
            "i" : protein[0],
            "filters": filters
            }
    
    
@router.get("/{feature_tag}/abundance") 
def get_feature_abundance(feature_tag : str, attribute_tag : str = None) -> QuantileModel|List[QuantileModel]:
    return DB.features.get_abundance_distribution(tag = feature_tag, attribute_tag = attribute_tag)


@router.get("/{feature_tag}/data",
            response_model=FeatureDataResponseModel)
def get_dataset_data(feature_tag : str, submission_tags : str = None,  max_datasets : int = 200, user : UserModel = Depends(get_user_from_token)):
    """
    Returns the data for a specific feature in all datasets it was detected in. 
    
    API Endpoint
    ------------
    ``GET api/features/{feature_key}/data```
    
    Parameters
    ----------
    feature_key : str
        The key of the feature (UniprotID).
    user : UserModel
        The user that was identified by the token.
    
    Returns
    -------
    FeatureDataResponseModel

    
    """
    

    feature_data = DB.features.get_data(tags=[feature_tag], 
                                        submission_tags=APIParamString(param=submission_tags).param)
    submission_tags = feature_data["submission_tag"].unique().tolist()
    attribute_value_tags = feature_data["attribute_value_tag"].unique().tolist() 
    attribute_tags = feature_data["attribute_tag"].unique().tolist() 
    genotype_tags = feature_data[feature_data["attribute_tag"] == "att_genotype"]["attribute_value_tag"]
    response_data = OrderedDict()#
    sample_attributes_by_submission_tag = {}
    #groupby tag and submission tag. This is too because the get_data function can be used to 
    #retrieve data formore than one feature tag. However this is impossible due to the API route. 
    #TO DO just ignore this here? 
    for (_, submission_tag), data in feature_data.groupby(by=["tag","submission_tag"]):
        
        pivot_attributes = data[["sample_index",
                                "attribute_tag",
                                "attribute_value_tag",
                                "submission_tag"]].pivot_table(columns=["attribute_tag"],
                                                                values="attribute_value_tag", 
                                                                index="sample_index", 
                                                                aggfunc=lambda x : x)
        data_transformed = data[["sample_index","value"]].drop_duplicates("sample_index").set_index("sample_index").join(pivot_attributes)
        response_data[submission_tag]  = data_transformed.sort_index().reset_index().to_dict(orient="records")
        #if submission_tag not in sample_attributes_by_submission_tag:
        sample_attributes_by_submission_tag[submission_tag] = data["attribute_tag"].unique().tolist()
            
        #
    #get minimal meta information 
    submission_meta = DB.meta.get(tags=submission_tags)
    print(response_data)
    
    attributes = DB.attributes.get(tags = attribute_tags)
    attribute_values = DB.attributes.get_values(tags = attribute_value_tags)
    genotypes = DB.genotypes.get(tags = genotype_tags)

    # db = MCDatabase.getDatabase()
    # db_helper = MCDatabaseHelper.getDatabaseHelper()
    # #dataset labels that contain the feature
    # dataset_labels = db_helper.get_labels_by_feature(feature_key)
    # #dataset_labels = db.getDataLabels()


    rsp = FeatureDataResponseModel(
        sample_attribute_by_submission_tag = sample_attributes_by_submission_tag,
        tag = feature_tag,
        data = response_data,
        submission_tags = submission_tags,
        attributes = dict([(a.tag,a) for a in attributes]),
        attribute_values_by_tag = dict([(av.tag,av) for av in attribute_values]),
        title_by_tag = dict([(meta_data.tag, meta_data.title) for meta_data in submission_meta]),
        genotypes_by_tag = dict([(g.tag,g) for g in genotypes])
    )
    
    return rsp 


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
def get_feature_variance(feature_tag : str, submission_tags : str = None):
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
    
    f_stats = DB.features.get_f_value(tags=[feature_tag], submission_tags=APIParamString(submission_tags).param)
    return f_stats.to_dict(orient="records")
    
    

@router.get("/{feature_tag}/abundance")
def get_feature_variance(feature_tag : str, submission_tags : str = None):
    """Returns the log2 average abundance per submission
    TODO: Should we implement that this returns also the attributes/traits
    This would allow to get a graphical representation depending on the datasets.
    """
    avg_abundance = DB.features.get_avg_abundance(tags = [feature_tag], submission_tags=APIParamString(submission_tags).param)
    return avg_abundance.to_dict(orient="records")
    


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
    
    
    

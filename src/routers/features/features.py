from fastapi import APIRouter, Depends, HTTPException
from typing import List
import pandas as pd 
from typing import Dict 
from config.models.user import UserModel
from config.models.annotations.feature import FeatureDataResponseModel, FeatureModel
from config.enums.states import SubmissionStatesEnums
from lib.data.annotations.ABCAnnotations import AnnotationDatabase
from services.users import get_user_from_token
from services.submission import map_tags_to_attribute_in_metadata
from lib.data.annotations.ABCAnnotations import PandaFeatureDatabase
from config.models.parameter import APIParamString
from lib.data.database.ABCDatabase import MCDatabase
from lib.data.transform.FeatureData import FeatureData
from lib.data.database_helper.ABCDatabaseHelper import MCDatabaseHelper
from lib.data.database.Database import Database

from config.exceptions.HTTPExceptions import protein_not_found
from collections import OrderedDict
DB = Database.DB()


router = APIRouter(
    prefix="/api/features",
    tags=["Features"]
    )

@router.get("")
def get_features_by_query(query : str, proteome_tags : str = None, limit : int = 30):
    """Finds query by feautre 

    Parameters
    ----------
    query : str
        The query string 
    proteome_ids : str, optional
        The list of proteomes to query the feature in. If None, alle available features will be searched for
        If multiple proteomes should be provided, separate them by a semicolon. 
    limit : int, optional
        The maximum number of features to be returned.
    user : UserModel, optional
        _description_, by default Depends(get_user_from_token)

    Returns
    -------
    _type_
        _description_
    """
    return DB.features.find(query, proteome_tags = APIParamString(param=proteome_tags).param, limit = limit)
    


@router.get("/{feature_tag}/i")
def get_feature_info(feature_tag : str):
    "" 
    protein = DB.features.get_protein_by_tags(tags = [feature_tag], as_data_frame=False) 
    if len(protein) == 0: raise protein_not_found
    filters = DB.filters.get(feature_tag=feature_tag)
    #DB.features.get_quant_stats(tags = [feature_tag])

    return {
            "i" : protein[0],
            "filters": filters
            }
    
    



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
    print(feature_data)
    submission_tags = feature_data["submission_tag"].unique().tolist()
    attribute_value_tags = feature_data["attribute_value_tag"].unique().tolist() 
    attribute_tags = feature_data["attribute_tag"].unique().tolist() 
    genotype_tags = feature_data[feature_data["attribute_tag"] == "att_genotype"]["attribute_value_tag"]
    print(attribute_tags, attribute_value_tags)
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
    
    attributes = DB.attributes.get(tags = attribute_tags)
    attribute_values = DB.attributes.get_values(tags = attribute_value_tags)
    print(attribute_values,"WHATS GOING ON HERE?")
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
    
    print(rsp)
    return rsp 
    
    
    
    
    # feature_data_by_dataset_label : Dict[str,pd.DataFrame] = {}
    # attributes_sample_by_dataset_label : Dict[str,Dict] = {}
    # attribute_samples_by_sample_collection = {}
    # attribute_values_by_tag_collection = {}
    # attributes_collection = {}
    # genotypes_by_dataset_label = {}
    # title_by_label = {}
    # for label in dataset_labels:
    #     dataset = db.getDataset(label=label)
    #     metadata = dataset.getMetaJson()
        
    #     if dataset.hasData() and metadata.state == SubmissionStatesEnums.ACTIVE:
    #         feature_data, attributes_samples, annotations = FeatureData(dataset).transform(feature_key, add_annotations=True)

    #         if not feature_data.empty and isinstance(feature_data,pd.DataFrame):
    #             updated_metadata = map_tags_to_attribute_in_metadata(metadata)
    #             #TODO this is something we could cash as as well? Mapping the tags from the DB to the actual attributes
    #             feature_data_by_dataset_label[label] = feature_data
    #             attributes_sample_by_dataset_label[label] = attributes_samples
    #             genotypes_by_dataset_label[label] = updated_metadata.genotypes
    #             ##update the attribute/attribute_value details to get the complete set of attributes required
    #             attribute_samples_by_sample_collection.update(updated_metadata.samples_attributes_by_sample)
    #             attribute_values_by_tag_collection.update(updated_metadata.attribute_values_by_tag)
    #             attributes_collection.update(updated_metadata.attributes)
    #             title_by_label[label] = metadata.title
    
    response_data = {
        "feature_key": feature_key,
        "title_by_label" : title_by_label,
        "dataset_labels" : list(feature_data_by_dataset_label.keys()),
        "data" : dict([(data_label,data_frame.reset_index(names="index").to_dict(orient="records")) for data_label, data_frame in feature_data_by_dataset_label.items()]),
        "samples_attributes" : attributes_sample_by_dataset_label,
        "attribute_values_by_tag" : attribute_values_by_tag_collection,
        "samples_attributes_by_sample" : attribute_samples_by_sample_collection,
        "attributes" : attributes_collection,
        "genotypes_by_label" : genotypes_by_dataset_label
        }
    #FeatureDataResponseModel(**response_data)
    return response_data



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
def get_feature_sequence(feature_tag : str): #user : UserModel = Depends(get_user_from_token)
    """
    Returns the sequence for a specific feature_key (Uniprot ID)
    
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
    
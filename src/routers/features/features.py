from fastapi import APIRouter, Depends, HTTPException
from typing import List
import pandas as pd 
from typing import Dict 
from config.models.user import UserModel
from config.models.annotations.feature import FeatureDataResponseModel, FeatureModel
from config.enums.states import SubmissionStates
from lib.data.annotations.ABCAnnotations import AnnotationDatabase
from services.users import get_user_from_token
from services.submission import map_tags_to_attribute_in_metadata
from lib.data.annotations.ABCAnnotations import PandaFeatureDatabase

from lib.data.database.ABCDatabase import MCDatabase
from lib.data.transform.FeatureData import FeatureData
from lib.data.database_helper.ABCDatabaseHelper import MCDatabaseHelper

router = APIRouter(
    prefix="/api/features",
    tags=["Features"]
    )

@router.get("")
def get_features_by_query(query : str, proteome_ids : str = None, max_features : int = 30):
    """_summary_

    Parameters
    ----------
    query : str
        _description_
    proteome_ids : UserModel, optional
        _description_
    max_features : UserModel, optional
        _description_
    user : UserModel, optional
        _description_, by default Depends(get_user_from_token)

    Returns
    -------
    _type_
        _description_
    """
    feature_db = PandaFeatureDatabase()
    if proteome_ids is None or len(proteome_ids) == 0:
        proteome_ids = list(feature_db.get_feature_ids())
    else:
        proteome_ids = proteome_ids.split(";")

    features = feature_db.find(values=[query], proteome_ids=proteome_ids, columns=["proteins", "genes","key"])

    if features.empty: return []

    if features.index.size > max_features:
        features = features.head(max_features)

    features = features.to_dict(orient="records")
    #features = features.to_dict(orient="records")  # [{'col1': 1, 'col2': 0.5}, {'col1': 2, 'col2': 0.75}]
    return [FeatureModel(**item) for item in features] 
    

@router.get("/{feature_key}/data",
            response_model=FeatureDataResponseModel)
def get_dataset_data(feature_key : str, max_datasets : int = 200, user : UserModel = Depends(get_user_from_token)):
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
    db = MCDatabase.getDatabase()
    db_helper = MCDatabaseHelper.getDatabaseHelper()
    #dataset labels that contain the feature
    dataset_labels = db_helper.get_labels_by_feature(feature_key)
    #dataset_labels = db.getDataLabels()
    
    feature_data_by_dataset_label : Dict[str,pd.DataFrame] = {}
    attributes_sample_by_dataset_label : Dict[str,Dict] = {}
    attribute_samples_by_sample_collection = {}
    attribute_values_by_tag_collection = {}
    attributes_collection = {}
    genotypes_by_dataset_label = {}
    title_by_label = {}
    for label in dataset_labels:
        dataset = db.getDataset(label=label)
        metadata = dataset.getMetaJson()
        
        if dataset.hasData() and metadata.state == SubmissionStates.PUBLISHED:
            feature_data, attributes_samples, annotations = FeatureData(dataset).transform(feature_key, add_annotations=True)

            if not feature_data.empty and isinstance(feature_data,pd.DataFrame):
                updated_metadata = map_tags_to_attribute_in_metadata(metadata)
                #TODO this is something we could cash as as well? Mapping the tags from the DB to the actual attributes
                feature_data_by_dataset_label[label] = feature_data
                attributes_sample_by_dataset_label[label] = attributes_samples
                genotypes_by_dataset_label[label] = updated_metadata.genotypes
                ##update the attribute/attribute_value details to get the complete set of attributes required
                attribute_samples_by_sample_collection.update(updated_metadata.samples_attributes_by_sample)
                attribute_values_by_tag_collection.update(updated_metadata.attribute_values_by_tag)
                attributes_collection.update(updated_metadata.attributes)
                title_by_label[label] = metadata.title
    
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



@router.get("/{feature_key}/variance")
def get_feature_variance(feature_key : str, labels : str = None):
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
    db_helper = MCDatabaseHelper.getDatabaseHelper()
    if labels is not None:
        labels = labels.split(";")
    df = db_helper.get_rel_variance_by_feature(feature_key)
    return df.to_dict(orient="records")
    
    

@router.get("/{feature_key}/abundance")
def get_feature_variance(feature_key : str, labels : str = None):
    db_helper = MCDatabaseHelper.getDatabaseHelper()
    if labels is not None:
        labels = labels.split(";")
    df = db_helper.get_abundance_by_feature(feature_key)
    return df.to_dict(orient="records")
    


@router.get("/{feature_key}/sequence",
            summary="Returns the stored sequence in the annotation database.")
def get_feature_sequence(feature_key : str): #user : UserModel = Depends(get_user_from_token)
    """
    Returns the sequence for a specific feature_key (Uniprot ID)
    
    API Endpoint
    ------------
    The API endpoint of this route HTTP method is : 
    ``GET  /api/features/{feature_key}/sequence``
    
    Parameters
    ----------
    feature_key : str 
        The feature_key to get the sequence from. 
    user : UserModel
        The user that was identified by the token.
    
    
    See also
    --------
    Please use the api endpoint /annotations to submit a list of feature_ids to 
    retrieve annotations efficiently. 
    """

    db_annotations = AnnotationDatabase()
    annotations = db_annotations.getAnnotations(feature_key=feature_key, subset=["SequenceAnnotation"])  # ToDo: What return Model is needed by GUI?
    if len(annotations) == 0: raise HTTPException(status_code=404, detail=f"No sequence annotations found for feature key {feature_key}.")
    sequence = list(annotations.values())[0][0]
    #TODO : the key of the sequence annotation is informative but overloaded? what happends if nothing found? 
    return {"feature_key" : feature_key, "sequence" : sequence}
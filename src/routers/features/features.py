from fastapi import APIRouter, Depends, HTTPException

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


router = APIRouter(
    prefix="/api/features",
    tags=["Features"]
    )


@router.get("")
def get_features_by_query(proteome_id : str, query : str, max_features : int = 30): #, user : UserModel = Depends(get_user_from_token)
    """_summary_

    Parameters
    ----------
    query : str
        _description_
    user : UserModel, optional
        _description_, by default Depends(get_user_from_token)

    Returns
    -------
    _type_
        _description_
    """
    feature_db = PandaFeatureDatabase()
    features = feature_db.find(values=[query], proteome_id=proteome_id)
    if features.empty: return []
    if features.index.size > max_features:
        features = features.head(max_features)
    features = features.reset_index(names="key").to_dict(orient="records")
    #features = features.to_dict(orient="records")  # [{'col1': 1, 'col2': 0.5}, {'col1': 2, 'col2': 0.75}]
    return [FeatureModel(**item) for item in features] 
    

@router.get("/{feature_key}/data",
            response_model=FeatureDataResponseModel)
def get_dataset_data(feature_key : str, user : UserModel = Depends(get_user_from_token), max_datasets : int = 200):
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
    dataset_labels = db.getDataLabels()
    feature_data_by_dataset_label : Dict[str,pd.DataFrame] = {}
    attributes_sample_by_dataset_label : Dict[str,Dict] = {}
    attribute_samples_by_sample_collection = {}
    attribute_values_by_tag_collection = {}
    attributes_collection = {}
    for label in dataset_labels:
        dataset = db.getDataset(label=label)
        metadata = dataset.getMetaJson()
        #TODO this is something we could cash as as well? Mapping the tags from the DB to the actual attributes
        
        
        if dataset.hasData() and metadata.state == SubmissionStates.PUBLISHED:
            feature_data, attributes_samples, annotations = FeatureData(dataset).transform(feature_key, add_annotations=True)
            #print(attributes_samples)
            if not feature_data.empty and isinstance(feature_data,pd.DataFrame):
                updated_metadata = map_tags_to_attribute_in_metadata(metadata)
                feature_data_by_dataset_label[label] = feature_data
                attributes_sample_by_dataset_label[label] = attributes_samples
                attribute_samples_by_sample_collection.update(updated_metadata.samples_attributes_by_sample)
                attribute_values_by_tag_collection.update(updated_metadata.attribute_values_by_tag)
                attributes_collection.update(updated_metadata.attributes)
    response_data = {
        "feature_key": feature_key,
        "dataset_labels" : list(feature_data_by_dataset_label.keys()),
        "data" : dict([(data_label,data_frame.reset_index(names="index").to_dict(orient="records")) for data_label, data_frame in feature_data_by_dataset_label.items()]),
        "samples_attributes" : attributes_sample_by_dataset_label,
        "attribute_values_by_tag" : attribute_values_by_tag_collection,
        "samples_attributes_by_sample" : attribute_samples_by_sample_collection,
        "attributes" : attributes_collection
        }
    FeatureDataResponseModel(**response_data)
    return response_data


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
    print(annotations)
    if len(annotations) == 0: raise HTTPException(status_code=404, detail="No sequene annotations found.")
    sequence = list(annotations.values())[0][0]
    #TODO : the key of the sequence annotation is informative but overloaded? what happends if nothing found? 
    return {"feature_key" : feature_key, "sequence" : sequence}
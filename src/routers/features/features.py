from fastapi import APIRouter, Depends

import pandas as pd 
from typing import Dict 
from config.models.user import UserModel
from config.models.annotations.feature import FeatureDataResponseModel
from lib.data.annotations.ABCAnnotations import AnnotationDatabase
from services.users import get_user_from_token

from lib.data.database.ABCDatabase import MCDatabase
from lib.data.transform.FeatureData import FeatureData


router = APIRouter(
    prefix="/api/features",
    tags=["Features"]
    )

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

    for label in dataset_labels:
        dataset = db.getDataset(label=label)
        if dataset.hasData():
            feature_data, attributes_samples, annotations = FeatureData(dataset).transform(feature_key, add_annotations=True)
            if not feature_data.empty and isinstance(feature_data,pd.DataFrame):
                feature_data_by_dataset_label[label] = feature_data
                attributes_sample_by_dataset_label[label] = attributes_samples

    return {
        "feature_key": feature_key,
        "dataset_labels" : list(feature_data_by_dataset_label.keys()),
        "data" : dict([(data_label,data_frame.reset_index(names="index").to_dict(orient="records")) for data_label, data_frame in feature_data_by_dataset_label.items()]),
        "attributes_samples" : attributes_sample_by_dataset_label,
        "annotations" : annotations[feature_key]
        }


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
    #TODO : the key of the sequence annotation is informative but overloaded? 
    return {
        "feature_key" : feature_key, **annotations}
from fastapi import APIRouter, Depends

import pandas as pd 

from config.models.user import User 
from config.models.feature import FeatureDataResponse
from services.users import get_user_from_token

from lib.data.database.ABCDatabase import MCDatabase
from lib.data.transform.FeatureData import FeatureData


router = APIRouter(
    prefix="/api/features",
    tags=["Features"]
    )

@router.get("/{feature_id}/data", response_model=FeatureDataResponse)
def get_dataset_data(feature_id : str, user : User =  Depends(get_user_from_token)):
    """
    Returns the data for a specific feature
    
    """

    db = MCDatabase.getDatabase()
    dataIDS = db.getAllDataIDs()
    

    feature_data_by_dataset_label = {}
    attributes_sample_by_dataset_label = {}
    for dataset_label in dataIDS:
        dataset = db.getDataset(label=dataset_label)
        feature_data, attributes_samples = FeatureData(dataset).transform(feature_id)
        if feature_data.empty: continue 
        feature_data_by_dataset_label[dataset_label] =  feature_data
        attributes_sample_by_dataset_label[dataset_label] = attributes_samples
    return {
        "feature_id": feature_id, 
        "dataset_labels" : list(feature_data_by_dataset_label.keys()), 
        "data" : feature_data_by_dataset_label, 
        "attributes_samples" : attributes_sample_by_dataset_label
         } 

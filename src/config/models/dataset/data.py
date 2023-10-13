from pydantic import BaseModel
from pydantic import Field
from pydantic import field_serializer 
from typing import List, Dict, Any

import pandas as pd 

from config.settings.db import get_db_settings
from services.random_generators import get_random_string

DB_SETTINGS = get_db_settings()

class DataID(BaseModel):
    """DataID BaseModel"""
    id : str = Field(..., min_length = DB_SETTINGS.data_id_length, 
                     max_length = DB_SETTINGS.data_id_length, 
                     default_factory=lambda : get_random_string(N = DB_SETTINGS.data_id_length))

class API_DatasetData(BaseModel):
    """Dataset Response Model"""
    data_id : str
    data : List[Dict]
    params : Dict[str, Any]





class DatasetPCAResponse(BaseModel):
    """Dataset Repsonse model for a PCA"""
    projection : pd.DataFrame
    drivers : pd.DataFrame
    variance_explained : List[float]

    class Config:
        # TO DO: Make Basemodel with this by default..
        arbitrary_types_allowed = True
    
    @field_serializer("projection","drivers")
    def dataframe_to_json(dataframe : pd.DataFrame):
        return dataframe.reset_index(names="index").to_dict(orient="records")


    
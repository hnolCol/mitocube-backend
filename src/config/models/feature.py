from pydantic import BaseModel, field_serializer, field_validator, root_validator
from typing import List, Dict, Any
from collections import OrderedDict
import pandas as pd 


class FeatureDataResponse(BaseModel):
    """
    Response model for feature data.
    """
    status : str = "Ok"
    feature_id : str
    attributes_samples : Dict[str,Dict]
    dataset_labels : List[str] #labels of datasets
    data : Dict[str,pd.DataFrame] #data key - dataset_labe 

    class Config:
        arbitrary_types_allowed = True
    
    @field_serializer("data")
    def transform_data(data : Dict[str,pd.DataFrame]):
        """Transform the dataset to json"""
        return OrderedDict([(data_label,data_frame.reset_index(names="index").to_dict(orient="records")) for data_label, data_frame in data.items() if isinstance(data_frame,pd.DataFrame) and not data_frame.empty])




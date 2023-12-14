from pydantic import BaseModel, field_serializer, field_validator, root_validator
from typing import List, Dict, Any
from collections import OrderedDict
import pandas as pd 


class FeatureDataResponse(BaseModel):
    """
    Response model for feature data.
    """
    feature_id : str  # Todo: Rename to feature_key
    attributes_samples : Dict[str,Dict]
    dataset_labels : List[str] #labels of datasets
    data : Dict[str,List[Dict]] #data key - dataset_labe 

    


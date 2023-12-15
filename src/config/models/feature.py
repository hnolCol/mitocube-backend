from deprecated import deprecated
from pydantic import BaseModel  # , field_serializer, field_validator, root_validator
from typing import List, Dict  # , Any
# from collections import OrderedDict
# import pandas as pd


@deprecated("Please use FeatureDataResponseModel(BaseModel) in annotation.feature.py")
class FeatureDataResponseModel(BaseModel):
    """
    Response model for feature data.
    """
    feature_id : str
    attributes_samples : Dict[str,Dict]
    dataset_labels : List[str]  # labels of datasets
    data : Dict[str,List[Dict]]  # data key - dataset_label


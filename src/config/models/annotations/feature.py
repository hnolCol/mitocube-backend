from pydantic import BaseModel
from typing import Dict, List, Optional

class FeatureModel(BaseModel):
    """Base Model for a Feature"""
    key : str 
    tag : Optional[str] = None
    genes : str 
    proteins : str 
    organism : str
    aa_length : int
    reviewed : Optional[bool] = True 

class FeatureDataResponseModel(BaseModel):
    """
    Response model for feature data.
    
    Parameters
    ----------
    feature_key : str
        The key of the feature (UniprotID)
    dataset_labels : List[str]
        The list of dataset labels in which the feature_key has been found. 
    attribute_samples 
        The attribute samples in a dictionary. Keys are the 
        dataset labels, and values are the samples attributes. (sample_attribute.name -> List[AttributeValuesTag])
    annotations : Dict[str, List[str]]
        The annotations found in the database. Keys are presenting the Annotation Database Tag and values 
        are a list of annotations such as GO terms. 
    """
    feature_key : str
    attributes_samples : Dict[str, Dict[str,List[str]]]
    dataset_labels : List[str]  # labels of datasets
    data : Dict[str, List[Dict]]  # data key - dataset_label
    annotations : Dict[str, List[str]]

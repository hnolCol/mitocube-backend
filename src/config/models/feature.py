from deprecated import deprecated
from pydantic import BaseModel  # , field_serializer, field_validator, root_validator
from typing import List, Dict, Optional  # , Any
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


class FeatureNeoModel(BaseModel):
    """Base Model for a Feature"""
    tag : str
    gene_name : str 
    gene_names : str = None
    protein_name : str
    proteome_tag : str
    aa_length : int = None
    reviewed : Optional[bool] = True 




class FeatureGeneModel(BaseModel):
    
    tag : str #the id of the gene (change)
    gene_name : str 
    gene_version : int 
    gene_source : Optional[str] = None
    
    
    
class FeatureSequenceResponseModel(BaseModel):
    feature_tag : str 
    sequence : str 
    
    
    
class ProteinGroupSubmissionStatisticsModel(BaseModel):
    tag : str
    attribute_tag : str 
    submission_tag : str
    score : float
    mean : Optional[float] = 0.0
    quantified_in_samples : int
    p_value : float
    F : float
    eta_squared : float
    cohen_f : float
    exclusively_ca_tags : Optional[List[str]] = []
    max_fc : float
    std_means : float
    missingness : float
    n_groups : int
    exclusively : bool
    rank : int 
    FDR : float
    
    
class ExclusivelyQuantifiedModel(BaseModel):
    tag : str
    attribute_tag : str 
    stats_tag : str 
    mean : Optional[float] = 0.0
    exclusively_ca_tags : Optional[List[str]] = []
    quantified_in_samples : int = 0
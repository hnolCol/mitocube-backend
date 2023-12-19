from pydantic import BaseModel,Field
import time
from typing import List, Optional
from services.random_generators import get_random_string

class RunListRequestPropsModel(BaseModel):
    """
    Properties in an HTTP API Request
    """
    rows_first : bool = True
    aggregate_on : Optional[str] = None 
    scramble : bool = True 
    fractionate : bool = False 
    n_fractions : int = 0 
    free_plate_positions : List[List[List[bool]]]

class AnalyticRunModel(BaseModel):
    """
    BaseModel for an analytic run (e.g. LC-MS/MS run)
    This can be different from the sample since one can
    use fraction and/or pooling.
    """
    name : str
    label : str = Field(...,default_factory=get_random_string)
    measured_at : Optional[float] = None #timestamp 
    index : int  #order prior scramble
    measurement_index : int #Measurement index if not scrambled, equals index
    plate_index : int #
    column_index : int # the index of column in the plate (e.g. integer)
    row_index : int # the index of rows in the plate (e.g. integer)
    position_label : str # the label of the position
    aggregated_samples : List[int]


class RunListModel(BaseModel):
    created_at : float = Field(...,default_factory=time.time)
    dataset_label : str 
    n_runs : int 
    n_plates : int
    runs : List[AnalyticRunModel]
    user_label : str #user that created the run list 
    aggregated_on : Optional[str] = None
    fractionated : bool = False
    n_fractions : int
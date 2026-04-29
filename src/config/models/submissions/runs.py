from pydantic import BaseModel,Field, EmailStr, field_validator
import time
import datetime as dt
from typing import List, Optional
from services.random_generators import get_random_string
from services.date import get_time_stamp
class RunListRequestPropsModel(BaseModel):
    """
    Properties in an HTTP API Request

    Parameter
    ---------
    rows_first : bool, default True
        If true, rows will be filled first when creating the run list (e.g. A1, A2 for sample 1 - 2 instead of A1, B1, B2)
    aggreagate_on : str, optional 
        The name of the samples attributes that should be used for aggregating the sample list on. T
        his would mean that you can pool numerous samples together and would result in 
        less runs than samples. As an example, a SILAC based quantification experiment in proteomics could be such an example.
    scramble : bool, default True
        Scrambles the runs in the ```RunList``` will be in random order. Usefull to avoid time batch effects by measuring for example all genotypes in a row while
        the analytical method such as LC-MS/MS performance changes over time. 
    scramble_across_plates : bool, default False 
        If scrambled is performance and the number of runs requires that the samples are spread over multiple plates, 
        then the scrambling will be performed within each plate (False, default)
        while if ```True``` all runs across plates are scrambled. It defaults to False since some analytical systems can only host a single well plate. 
    fractionate : bool, default True
        If samples are fractionated, than the number of runs is higher than the number of samples. The number of fractions can be defined using ```n_fractions``` parameter. 
    n_fractions : int, default 0 
        The number of fractions each sample is fractionated in to. As an example, if an offline fractionation is performed 
        that results in six fractions, each sample then requires
        6 analytical runs. Please note that you can combine this with the ```aggregated_on```parameter which is allows 
        to define a pooling of the sample. As a practical example, 
        assume that a TMT-12 plex quantification strategy is performed, hence the samples are ```aggregated_on``` 
        the TMT-batch and then the pooled samples is fractionated via 
        offline high-pH fractionation, which results in a 24 fractions. 
    free_plate_positions : List[List[List[bool]]]
        List of plates (for example 96, 384) indicating which positions are free using bools. Each plate is again a list
        of lists (row1, row2, row3) where each row (column1, column 2). A 2 x 3 plate with the last well blocked would be:
        ```
        plate = [[True, True, True],[True, True, False]]
        ```
        The plate design can be different but for each plate the number of columns must be equal throughout the rows. 

    """
    rows_first : bool = True
    aggregate_on : Optional[str] = None 
    scramble : bool = True 
    scramble_across_plates : bool = False
    fractionate : bool = False 
    n_fractions : int = 0 
    free_plate_positions : List[List[List[bool]]]
    instrument_tag : str


class AnalyticRunModel(BaseModel):
    """
    BaseModel for an analytic run (e.g. LC-MS/MS run)
    This can be different from the sample since one can
    use fraction and/or pooling.
    """
    name : str
    # label : str = Field(...,default_factory=lambda : get_random_string(n=3))
    measured_at : Optional[float] = None #timestamp 
    index : int  #order prior scramble
    measurement_index : int #Measurement index if not scrambled, equals index
    plate_index : int #
    column_index : int # the index of column in the plate (e.g. integer)
    row_index : int # the index of rows in the plate (e.g. integer)
    position_label : str # the label of the position
    aggregated_samples : List[int]


class RunListModel(BaseModel):
    """
    The runlist model.

    """
    # user_label : str
    created_at : float = Field(...,default_factory=get_time_stamp)
    user_tag : Optional[str] = None #user that created the run list 
    dataset_label : str 
    n_runs : int 
    n_plates : int
    fractionated : bool = False
    n_fractions : int
    scrambled : bool
    scrambled_across_plates : bool = False
    runs : List[AnalyticRunModel]
    aggregated_on : Optional[str] = None
    instrument_tag : Optional[str] = None
    
    # @field_validator('user_tag', mode="after")
    # def check_user(cls, v : List[str]|str, field):
    #     ""
    #     if v is None:
            
    #         return cls.user_tag
    
    
    

class RunListResponseModel(RunListModel):
    """
    The model that is returned when a runlist is created to the browser.
    """
    user_email : EmailStr
    user_firstname : str 
    user_lastname : str 
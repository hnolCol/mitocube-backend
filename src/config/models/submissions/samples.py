from pydantic import BaseModel,Field
import time
from typing import List, Optional

class AnalyticRun(BaseModel):
    """
    BaseModel for an analytic run (e.g. LC-MS/MS run)
    This can be different from the sample since one can
    use fraction and/or pooling.
    """
    name : str
    positions : str 
    measured_at : float #timestamp 
    index : int  #order of measurement


class RunList(BaseModel):
    created_at : float = Field(...,default_factory=time.time)
    n_runs : int 
    runs : List[AnalyticRun]
    user_label : str #user that created the run list 
    aggregated_on : Optional[str] = None
    fractionated : bool = False
    n_fractions : int
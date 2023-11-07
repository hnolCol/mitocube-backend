from pydantic_settings import BaseSettings 
from pydantic import Field
import time 
import numpy as np 
from typing import Literal, List, Dict


class ProjectDescription(BaseSettings):
    """
    Base Settings for a Project
    This is used to define the minimal required information for a project.  
    """
    user_id : str 
    label : str # project label (id)
    title : str # proecjt title 
    state : str # state enum 
    metatext : str 
    created_on : float = Field(default_factory= time.time) 
    modified_on : float = None 
    attributes : np.ndarray
    group_attribues : np.ndarray  #attributes accessible to statistics 
    timetine : List[Dict] #time line of a project consists out of items in a list ordered by time


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

    


        #  self._refresh()

        # return {"id": self._id,
        #         "label": self._label,
        #         "state": self._state,
        #         "title": self._title,
        #         "experimentator": self._experimentator,
        #         "group_name": self._name_group,
        #         "email": self._contact_email,
        #         "date_created_on": self._created_on,
        #         "date_uploaded_on": self._uploaded_on,
        #         "instrument": self._instrument,
        #         "n_rows": self._cached_data_table.shape[0],
        #         "n_samples": self._cached_data_table.shape[1],
        #         "metatexts": self._metatexts,
        #         "urls": self._urls,
        #         "replicates": self._replicates,
        #         "attributes": self._attributes_dataset,
        #         "n_attributes": len(self._attributes_dataset),
        #         "group_attributes": self._attributes_samples,
        #         "n_group_attributes": len(self._attributes_samples)}
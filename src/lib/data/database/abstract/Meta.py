from __future__ import annotations

from abc import abstractmethod, ABC
from collections import OrderedDict
# from datetime import timedelta
from typing import List, Dict, Optional, Tuple, Literal  # , Any
from deprecated import deprecated
from neo4j import Driver 

import pandas as pd

from lib.data.dataset.ABCDataset import MCDataset
from lib.DesignPatterns import SingletonABCMeta  # , ExpiringValue
from lib.data.database.abstract.Attributes import AttributesABC

from config.settings.db import get_db_settings
from config.models.attributes import AttributeModel, AttributeUnitResponseModel
from config.models.submissions.submissions import DatasetSubmissionModel
from config.models.user import UserModel 
from config.models.feature import FeatureNeoModel
from config.models.filter import Filter


class MetaABC(ABC):
    
    def __init__(self, *args, **kwargs) -> None:
        ""
    
    @abstractmethod
    def add_owner(self, tag : str, user_tag : str):
        """Add an owner. Since there is only
        a single owner allowed per submission/dataset,
        this replaces the 'old' owner. 

        Parameters
        ----------
        tag : str
            _description_
        user_tag : str
            _description_
        """


    @abstractmethod
    def add_collaborators(self, tag : str, user_tags : List[str]):
        """Adds collaborators to a given
        submission/dataset.

        Parameters
        ----------
        tag : str
            The submission/dataset tag 
        user_tags : List[str]
            The list of collaborators given by a list of tags. 
        """
       
    @abstractmethod    
    def get(self, tags : List[str]) -> List[Dict]:
        """Retrieve the minimal information about a dataset. 

        Parameters
        ----------
        tags : List[str]
            The submission/dataset_tag for which the metadata should be retrieved.

        Returns
        -------
        List[Dict]
            The minimal metadata of a dataset. 

        Raises
        ------
        Exception
            If the database throws an Exception
        """
        
    @abstractmethod
    def update_owner(self, tag : str, user_tag : str):
        """Updates the ownership of data submission/dataset.

        Parameters
        ----------
        tag : str
            The tag associated with the submission / dataset 
        user_tag : str
            The tag that defines the user. 

        Returns
        -------
        _type_
            _description_

        Raises
        ------
        Exception
            If the database query resulted in an error. 
        """
    
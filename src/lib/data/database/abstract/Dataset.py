
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
   
    
class DatasetABC(ABC):
    def __init__(self, *args, **kwargs) -> None:
        ""

    @abstractmethod
    def get(self, tags : List[str]) -> List[str]:
        """Returns the minimal meta information of a dataset

        Parameters
        ----------
        tags : List[str]
            The list of tags that the minimal metadata should be returned. 

        Returns
        -------
        List[str]
            _description_
        """
    
    @abstractmethod
    def get_metatext(self, tags : List[str]) -> pd.DataFrame:
        """Returns the metatext that is associated with 
        the provided dataset_tags

        Parameters
        ----------
        tags : List[str]
            The tag associated with the dataset. 
            
        Returns
        -------
        pd.DataFrame
            The metatext given in a pandas data frame with 
            the following columns:
            
                - 'tag' (str) : The dataset tags. If multiple metatext are
                present for the tag, each metatext is in a separate row (e.g. duplicates)
                
                - 'meta_tag' (str) : The tag that was given to the metatext 
                
                - 'content' (str) : The actual content of the metatext. 
        """
        
    @abstractmethod
    def get_sample_attributes(self, tag : str) -> Dict[str,Dict[str,List[int]]]:
        """Describes the attributes that were assigned to each sample.

        Parameters
        ----------
        tag : str
            The dataset tag for which the sample attributes
            should be returned. 

        Returns
        -------
        Dict[str,Dict[str,List[int]]]
            ```
            {'attribute_tag' : {'attribute_value_tag' : List[sample indices (int) ]}}
            ```
        """
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



class FilterABC(ABC):
    """Filters handle the available 
    filter (set of proteins) that can 
    be used by the user to create a subset of the 
    data. For example, the MitoCarta 3.0 
    is simply a list of proteins that can be used
    to subset a volcano plot or a heatmap. 
    Filters are proteome_id sepcific. 
    """

    @abstractmethod
    def add(self, protein_tags : List[str], 
            proteome_id : str, 
            filter_tag : str, 
            description : str,
            publication : Optional[str] = None) -> Tuple[bool,str]:
        """Adds a filter to the database. 

        Parameters
        ----------
        protein_tags : List[str]
            _description_
        proteome_id : str
            _description_
        filter_tag : str
            _description_
        description : str
            _description_
        publication : Optional[str], optional
            _description_, by default None
        """
    
    @abstractmethod
    def get(self, tag : str = None) -> List[Filter]:
        """Returns the metadata of the available 
        filters/protein sets from the database.

        Parameters
        ----------
        tag : str
            The filter tag

        Returns
        -------
        List[Filter]
            The filters detected in the database. All if tag is None. 
            Otherwise a subset. 
        """
        
    @abstractmethod    
    def get_features(self, tag : str) -> List[FeatureNeoModel]:
        """Returns the list of proteins as a feature model that
        are associated with the provided tag. 

        Parameters
        ----------
        tag : str
            The filter tag. 

        Returns
        -------
        List[FeatureNeoModel]
            _description_

        Raises
        ------
        Exception
            If the database query returns an error. 
        """

    
    
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
    
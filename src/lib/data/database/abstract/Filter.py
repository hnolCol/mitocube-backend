from __future__ import annotations
from abc import abstractmethod, ABC

from typing import List, Dict, Optional, Tuple
from deprecated import deprecated

from config.models.user import UserModel 
from config.models.feature import FeatureNeoModel
from config.models.filter import FilterModel

import pandas as pd 


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
            proteome_tag : str, 
            filter_tag : str, 
            description : str,
            publication : Optional[str] = None) -> Tuple[bool,str]:
        """Adds a filter to the database. 

        Parameters
        ----------
        protein_tags : List[str]
            _description_
        proteome_tag : str
            _description_
        filter_tag : str
            _description_
        description : str
            _description_
        publication : Optional[str], optional
            _description_, by default None
        """
    @abstractmethod 
    def count_feaures(self, tag : str)  -> int:
        """Counts the number of features (e.g. the size
        of the filter.) 

        Parameters
        ----------
        tag : str
            The filter tag 

        Returns
        -------
        int
            The size (e.g. number of features).
            If the tag does not exists, 0 will be returned. 
        """
    
    
    @abstractmethod
    def get(self, tag : str = None, proteome_tags : List[str] = None, feature_tag : str = None) -> List[FilterModel]:
        """Returns the details of the available 
        filters/protein sets from the database.

        Parameters
        ----------
        tag : str
            The specific filter tag to be returned, default None
            If a tag is provided, the other arguments are ignored. 
        proteome_tags : List[str]
            List of proteome tags. If just proteome tags are given, then all 
            filters of a specific proteome are returned, ignored of tag is given. 
        feature_tag : str 
            A feature tag that must be in the filter, ignore if tag is or proteome_tags is provided.     
        
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
            . 
        """
        
    
    @abstractmethod
    def isin(self, tag : str, feature_tags : List[str]) -> pd.Series:
        """Checks if the given feature tags are in the
        filter (given by its tag. )

        Parameters
        ----------
        tag : str 
            The filter tag. 
            
        feature_tag : List[str]
            _description_

        Returns
        -------
        pd.Series
            pandas Series with bools to indicate
            if the given feature is present. 
            If the tag does not exists, and empty Series will be returned
        """

    

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
   
   
   
class FeaturesABC(ABC):
    """
    Features (proteins) can be added only from an uniprot
    reference proteome. An should be added using the insert_uniprot_proteome function. 
    Feature should not be updated for a proteome by the admin. 
    There is a common protein sequence file which can be used to define
    'custom' proteins such as controls. 
    """
    
    @abstractmethod
    def find(self, search_string : str, proteome_ids : List[str]) -> List[FeatureNeoModel]:
        """Search the feature database by a search string.

        Parameters
        ----------
        search_string : str
            _description_
        proteome_ids : List[str]
            The proteome ids to search in. 

        Returns
        -------
        List[FeatureNeoModel]
            _description_
            
        Exception 
        ---------
        
        ValueError 
            If any of the given proteome_ids does not exist.     
        
        """
    
    
    @abstractmethod
    def get_protein_sequence(self, tags : str) -> List[str]:
        """Returns the protein sequences for the given tags

        Parameters
        ----------
        tags : str
            Feature/protein tags

        Returns
        -------
        List[str]
            Protein sequences in a list.
        """
        
    @abstractmethod
    def get_protein_by_tags(self, tags : List[str], as_data_frame : bool = True) -> List[FeatureNeoModel]|pd.DataFrame:
        """Returns the protein information from the database

        Parameters
        ----------
        tags : List[str]
            The protein tags
        as_data_frame : bool, optional
            If the data should be returned as a pandas data frame, by default True

        Returns
        -------
        List[FeatureNeoModel]|pd.DataFrame
            if as_data_frame is True, then a pandas data frame is returned, otherwise a list of FeatureModel is returned
        """
    
    @abstractmethod
    def insert_uniprot_proteome(self, 
                                proteome_id : List[str] = ["UP000005640"], 
                                reviewed : bool = True, 
                                user_tag : str = None) -> int:
        """Insert the data from the Uniprot Database for a reference proteome. 

        Parameters
        ----------
        proteome_id : List[str], optional
            _description_, by default ["UP000005640"]
        reviewed : bool, optional
            _description_, by default True
        user_tag : str, optional
            _description_, by default None

        Returns
        -------
        int
            The number of proteins added to the database. 

        Raises
        ------
        Exception
            If the database insertion throws an Exception. 
        """
from __future__ import annotations
from abc import abstractmethod, ABC

from typing import List, Dict, Optional, Tuple
from deprecated import deprecated

from config.models.user import UserModel 
from config.models.feature import FeatureNeoModel
from config.models.filter import FilterModel

import pandas as pd 


class ProteinGroupsABC(ABC):
    ""
    
    @abstractmethod
    def get(self, tag : str) -> Dict:
        """Returns the protein group information for a given tag

        Parameters
        ----------
        tag : str
            The protein group tag 

        Returns
        -------
        Dict
            A dictionary with the protein group information. 
            If the tag does not exist, an empty dictionary is returned. 
        """
        
    @abstractmethod
    def count(self, submission_tag : str) -> int:
        """Returns the number of protein groups for a given submission.
        If the submission tag does not exist, 0 is returned.

        Parameters
        ----------
        submission_tag : str
            The submission tag 

        Returns
        -------
        int
            The number of protein groups for the given submission.
            If the submission does not exist, 0 is returned. 
        """
        
    @abstractmethod    
    def exists(self, tag : str) -> bool:
        """If a protein group tag exists. 

        Parameters
        ----------
        tag : str
            The protein group tag 

        Returns
        -------
        bool
            True if the tag exists, False otherwise. 
        """
        
        
    @abstractmethod
    def find(self, search_string : str, limit : int = None) -> List[str]:
        """Finds all protein group tags matching the search string.

        Parameters
        ----------
        search_string : str
            The search string to match against protein group tags.
        limit : int, optional
            If provided, limits the number of results returned, by default None

        Returns
        -------
        List[str]
            A list of protein group tags matching the search string.
        """
    
    @abstractmethod
    def get_proteins(self, tag : str) -> List[str]:
        """Returns the list of protein tags that are part of the protein group.

        Parameters
        ----------
        tag : str
            The protein group tag 

        Returns
        -------
        List[str]
            A list of protein tags that are part of the protein group.
            If the tag does not exist, an empty list is returned. 
        """
    
    @abstractmethod
    def insert(self, tag : str, protein_tags : List[str]) -> bool:
        """Adds a protein group to the database. 

        Parameters
        ----------
        tag : str
            The protein group tag 
        protein_tags : List[str]
            The list of protein tags that are part of the protein group.

        Returns
        -------
        bool
            True if the insertion was successful, False otherwise.
        """
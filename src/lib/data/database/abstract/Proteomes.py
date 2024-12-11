from __future__ import annotations
from abc import abstractmethod, ABC

from typing import List, Dict, Optional, Tuple
from deprecated import deprecated

import pandas as pd

from config.models.user import UserModel 
from config.models.feature import FeatureNeoModel
from config.models.filter import FilterModel


class ProteomeModel:
    tag : str 
    text : str #
    organism : str 
    description : str 
    N : int #number of features 
    
    
class ProteomesABC(ABC):
    

        
    @abstractmethod
    def count(self) -> int:
        """Returns the number of proteomes in 
        the database. 

        Returns
        -------
        int
            _description_
        """
        
    @abstractmethod 
    def delete(self, tag : str) -> bool:
        """Deletes a specific proteome by its tag. 

        Parameters
        ----------
        tag : str
            The tag of the Uniprot Proteome (starts with UP...)

        Returns
        -------
        bool
            Indicates if the deletion was successful. 
        """
        
        
    @abstractmethod
    def exist(self, tags : str|List[str]) -> bool:
        """Checks if the given tags of the proteome exist
        in the database. 

        Parameters
        ----------
        tags : str | List[str]
            _description_

        Returns
        -------
        bool
            If all tags exist. 
            
        Raises
        ------
        ValueError - if any of the tags does not exist.
        """
        
    @abstractmethod
    def find_features(self, query : str, proteome_tags : str|List[str] = None, limit : int = 10) -> List[Dict]:
        """Returns a list of features that are found by a query string. 

        Parameters
        ----------
        query : str, optional
            _description_, by default "FB"
        proteome_id : str|List[str], optional
            The proteome_tags(Uniprot)

        Returns
        -------
        List[FeatureNeoModel]
            The list of features in the database that match the query.
            The list has a maximum length of limit. 
        """
        
        
    @abstractmethod
    def get(self) -> Dict:
        """Returns a specific proteome details
        TODO: Create proteome model 
        Returns
        -------
        Dict
            _description_
        """
    
    @abstractmethod
    def get_features(self, tag : str) -> List[FeatureNeoModel]:
        """Returns the features/proteins that are part of a specific proteome,
        given by the proteome tag. 

        Parameters
        ----------
        tag : str
            _description_

        Returns
        -------
        List[FeatureNeoModel]
            _description_
        """
        
    @abstractmethod
    def insert_uniprot_proteome(self, 
                                proteome_tag : List[str] = ["UP000005640"], 
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
        
    @abstractmethod
    def insert_proteome_from_dataframe(self, data : pd.DataFrame, proteome_tag : str = "UP000005640", user_tag : str = None): 
        """Insert data from a Uniprot reference proteome to the database. 

        Parameters
        ----------
        data : pd.DataFrame
            The protein data with the following headers
            
                - Length (int) : The number of amino acids
                - Gene names (str) : All gene names associated with the protein
                - Gene Names (primary) (str)
                - Protein Names (str) - The associated protein name 
                - Entry (str) : The Uniprot ID 
                - Sequence (str) : The protein sequence.
                
        proteome_tag : str, optional
            The Uniprot reference proteome ID, by default "UP000005640" (Human)
        user_tag : str, optional
            The tag associated with a user, by default None
        """
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
    def exists(self, tag : str) -> bool:
        """Checks if the given tag of the proteome exist
        in the database. 

        Parameters
        ----------
        tag : str
            The tag of the Uniprot Proteome (starts with UP...)

        Returns
        -------
        bool
            Indicates if the proteome exists. 
        """
       
    @abstractmethod
    def find_features(self, query : str, proteome_tags : str|List[str] = None, limit : int = 10) -> List[Dict]:
        """Returns a list of features that are found by a query string. 

            
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
    def find(self, search_string : str = None, limit : int = None) -> List[str]:
        """Finds proteome tags that match the search string. 

        Parameters
        ----------
        search_string : str, optional
            The search string to look for in the proteome tags., by default None
        limit : int, optional
            The maximum number of proteome tags to return., by default None

        Returns
        -------
        List[str]
            A list of matching proteome tags. 
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
    def get_proteome_by_protein_tag(self, protein_tag : str) -> str:
        "Returns the proteome tag associated with a given protein tag."
        
        
    @abstractmethod
    def get_text(self, tag : str) -> str:
        pass
    
    
    @abstractmethod
    def is_updating(self, tag : str) -> bool:
        """Returns if the proteome is currently updating

        Parameters
        ----------
        tag : str
            The tag of the proteome.
           

        Returns
        -------
        bool
            Indicates if the proteome is currently updating.
        """
        
    @abstractmethod
    def get_created_at(self, tag : str) -> float:
        """Returns the timestamp of the proteome creation.

        Parameters
        ----------
        tag : str
            The tag of the proteome.

        Returns
        -------
        float
            The creation timestamp of the proteome.
        """
        
    @abstractmethod
    def get_protein_count(self, tag : str) -> int:
        """Returns the number of proteins for a given proteome.

        Parameters
        ----------
        tag : str
            The tag of the proteome.

        Returns
        -------
        int
            The number of proteins associated with the proteome.
        """
    
    @abstractmethod
    def get_proteins(self, tag : str) -> List[str]:
        """Returns the tags of features associated with a proteome.

        Parameters
        ----------
        tag : str
            The tag of the proteome.

        Returns
        -------
        List[str]
            A list of feature tags associated with the proteome.
        """     

    @abstractmethod
    def set_updating(self, tag : str, updating : bool) -> bool:
        """Sets the updating state of the proteome.

        Parameters
        ----------
        tag : str
            The tag of the proteome.
        updating : bool
            The updating state to set.

        Returns
        -------
        bool
            Indicates if the operation was successful.
        """
    @abstractmethod
    def is_updating(self, tag : str) -> bool:
        """Returns if the proteome is currently updating

        Parameters
        ----------
        tag : str
            The tag of the proteome.
           

        Returns
        -------
        bool
            Indicates if the proteome is currently updating.
        """
        
    @abstractmethod
    def insert_uniprot_proteome(self, 
                                proteome_tags : List[str] = ["UP000005640"], 
                                reviewed : bool = True, 
                                user_tag : str = None) -> int:
        """Insert the data from the Uniprot Database for a reference proteome. 

        Parameters
        ----------
        proteome_tags : List[str], optional
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
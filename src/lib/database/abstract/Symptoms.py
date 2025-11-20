from __future__ import annotations
from abc import abstractmethod, ABC

from typing import List, Literal
from deprecated import deprecated

from config.models.symptoms import SymptomResponseModel, SymptomModel, SymptomInsertModel


class SymptomABC(ABC):
    """
    Symptoms describe a problem of the instrumentation, usually a LC-MS/MS system,
    but in principle any kind of the instrument problem may be described by a symptom. 

    Parameters
    ----------
    ABC : _type_
        The abstract class 
    """
    
    
    @abstractmethod
    def count(self) -> int:
        """Returns the number of symptoms in 
        the database. 

        Returns
        -------
        int
            The number of symptoms in the database.
        """

    @abstractmethod
    def delete(self, tag : str, is_active : bool) -> bool:
        """Deletes a symptom by its tag. 

        Parameters
        ----------
        tag : str
            The symptom tag.

        Returns
        -------
        bool
            Indicates if the deletion was successful. 
        """

    @abstractmethod
    def exists(self, tag : str) -> bool:
        """If a symptom with the given tag exists in the database. 

        Parameters
        ----------
        tag : str
            The symptom tag.

        Returns
        -------
        bool
            Indicates if the symptom exists. 
        """

        
    @abstractmethod
    def find(self, search_string : str = "", limit : int = 20, is_active : bool = True) -> List[str]:
        """Find symptoms by a search string. 

        Parameters
        ----------
        search_string : str, optional
            The query string, by default ""
        limit : int, optional
            The maximum number of symptoms to be returned., by default 20

        Returns
        -------
        List[str]
            The symptom tags. 
        """
        
    
    @abstractmethod
    def get(self, tag : str) -> SymptomResponseModel:
        """Returns symptoms in the database. 
        If tags is None, all symptoms will be returned. 

        Parameters
        ----------
        tag : str
            The symptom tag.

        Returns
        -------
        SymptomModel
            The symptom model.
        """
    
    @abstractmethod
    def insert(self, symptom : SymptomInsertModel, user_tag : str, is_active : bool = True) -> bool:
        """Inserts a symptom into the database. 

        Parameters
        ----------
        symptom : SymptomInsertModel
            The symptom to insert.
        user_tag : str
            The user tag of the user inserting the symptom.

        Returns
        -------
        bool
            Indicates if the insertion was successful.
        """ 
         
    
    @abstractmethod 
    def update(self, symptom : SymptomInsertModel, user_tag : str) -> bool:
        """Updates a symptom in the database. 

        Parameters
        ----------
        symptom : SymptomInsertModel
            The symptom to update.
        user_tag : str
            The user tag of the user updating the symptom.

        Returns
        -------
        bool
            Indicates if the update was successful.
        """
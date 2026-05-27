
from __future__ import annotations

from abc import abstractmethod, ABC
from collections import OrderedDict
# from datetime import timedelta
from typing import List, Dict, Optional, Tuple, Literal  # , Any
from deprecated import deprecated
from neo4j import Driver 
from config.models.conditions_applications import ConditionApplicationTreeModel
from config.models.attributes import AttributeTree
import pandas as pd


   
    
class ConditionApplicationABC(ABC):
    def __init__(self, *args, **kwargs) -> None:
        ""
    
    @abstractmethod 
    def exists(self, tag : str) -> bool: 
        """If a submission tag is associated with a condition application. 
        Condition applications are always associated with submissions, but such submissions that 
        have specific conditions applied to them.

        Parameters
        ----------
        tag : str
            _description_

        Returns
        -------
        bool
            _description_
        """
    
    @abstractmethod
    def find(self, search_string : str = None, samples_only : bool = True, submission_tag : str = None, attribute_tag : str = None, trait_tag : str = None, protein_tags : List[str] = None, sort_by_frequency : bool = True, limit : int = None, exclude_attribute_group : List[str] = None) -> List[str]:
        """Returns the tags of matching condition applications
        
        Parameters
        ----------
        samples_only : bool, optional
            If True, only return condition applications that are associated with samples not with submissions, by default True
        submission_tag : str, optional
            If provided, only return condition applications that are associated with the given submission tag. If
            samples_only is True, only samples of the particular submission are considered, by default None
        attribute_tag : str, optional
            If provided, only return condition applications that are associated with the given attribute tag, by default None
        trait_tag : str, optional
            If provided, only return condition applications that are associated with the given trait tag, by default None
        sort_by_frequency : bool, optional
            If True, sort the results by the most frequent condition applications, by default True
        limit : int, optional
            If provided, limit the number of results returned, by default None

        Returns
        -------
        List[str]
            A list of condition application tags matching the query criteria.
        """
        
        
    @abstractmethod
    def get(self, tag: str) -> Dict:
        "Return the condition application details."
    
    @abstractmethod
    def get_attribute(self, tag: str) -> str:
        "Return the attribute tag of the condition application. Only the first level attribute is returned."  
        
        
        
    @abstractmethod
    def get_tree(self, tag : str) -> ConditionApplicationTreeModel:
        """Returns a hierarchical tree representation of the condition application.
        """

    # @abstractmethod
    # def transform_for_ui(self, tag : str) -> ConditionApplicationTreeModel:
    #     """Transforms a dictionary representation of a condition application into a hierarchical tree structure.
    #     """
    @abstractmethod
    def get_text(self, tag : str) -> str:
        "Return a human-readable text representation of the condition application."
    
    @abstractmethod
    def get_trait(self, tag: str) -> str:
        "Return the trait tag of the condition application. Only the first level trait is returned."  
    
    @abstractmethod
    def insert(self, condition_application : AttributeTree, extra_data_for_hash : Dict = {}) -> bool:
        """Inserts a new condition application into the database.

        Parameters
        ----------
        condition_application : Dict
            The condition application data to insert.

        Returns
        -------
        bool
            True if the insertion was successful, False otherwise.
        """

    @abstractmethod
    def has_value(self, tag: str) -> bool:
        """Checks if the condition application has a value (i.e., is associated with a protein).

        Parameters
        ----------
        tag : str
            The tag of the condition application to check.

        Returns
        -------
        bool
            True if the condition application has a value, False otherwise.
        """

    @abstractmethod
    def delete(self, tag: str) -> bool:
        """Deletes a condition application from the database.

        Parameters
        ----------
        tag : str
            The tag of the condition application to delete.

        Returns
        -------
        bool
            True if the deletion was successful, False otherwise.
        """
        
        
        
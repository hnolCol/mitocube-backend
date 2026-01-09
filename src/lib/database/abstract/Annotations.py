from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Optional, Tuple
import pandas as pd

from config.models.annotations.annotations import ( AnnotationModel, AnnotationGroupModel)

class AnnotationGroupABC(ABC):
    """
    Abstract class for annotation group.
    Annotation groups organize annotation datasets.
    """

    @abstractmethod
    def exists(self, tag: str) -> bool:
        """
        Check if an annotation group exists.

        Parameters
        ----------
        tag : str
            Annotation group tag.

        Returns
        -------
        bool
            True if the group exists.
        """
        

    @abstractmethod
    def insert(self, annotationgroup: AnnotationGroupModel) -> bool:
        """
        Create a new annotation group.

        Parameters
        ----------
        annotationgroup : AnnotationGroupModel
            Annotation group data.

        Returns
        -------
        bool
            True if insert was successful
        """
        

    @abstractmethod
    def get(self, tag: str) -> AnnotationGroupModel:
        """
        Gets the annotation group by tag.

        Parameters
        ----------
        tag : str
            Annotation group tag.

        Returns
        -------
        AnnotationGroupModel
            The annotation group model.
        """
        

    @abstractmethod
    def find(self) -> List[AnnotationGroupModel]:
        """
        Finds all annotation groups.

        Returns
        -------
        List[AnnotationGroupModel]
            All annotation groups.
        """
        

    @abstractmethod
    def get_annotations(self, group_tag: str) -> List[str]:
        """
        Return annotation tags belonging to a group.

        Parameters
        ----------
        group_tag : str
            Annotation group tag.

        Returns
        -------
        List[str]
            Annotation tags.
        """
        

class AnnotationABC(ABC):
    """
    Abstract class for annotation datasets.
    Each annotation represents a dataset/list of features/Proteins.
    """

    @abstractmethod
    def exists(self, tag: str) -> bool:
        """
        Check if an annotation exists.

        Parameters
        ----------
        tag : str
            Annotation tag.

        Returns
        -------
        bool
            True if the annotation exists.
        """
        

    @abstractmethod
    def add( self, annotation: AnnotationModel) ->bool:
        """
        Create a new annotation dataset and link protein identifiers.

        Parameters
        ----------
        annotation : AnnotationModel
            Annotation data.

        Returns
        -------
        bool
           True if insert was successful.
        """
        

    @abstractmethod
    def get(self, tag: str) -> AnnotationModel:
        """
        Gets annotation data by its tag.

        Parameters
        ----------
        tag : str
            Annotation tag.

        Returns
        -------
        AnnotationModel
            Annotation data.
        """
        

    @abstractmethod
    def find(self, group_tag: Optional[str] = None, protein_id: Optional[str] = None) -> List[str]:
        """
        Find annotations.

        Parameters
        ----------
        group_tag : Optional[str]
            Search within a specific annotationn group
        protein_id : Optional[str]
            Search to annotations containing this protein.

        Returns
        -------
        List[str]
            Matching annotation tags.
        """
        

    @abstractmethod
    def count_proteins(self, tag: str) -> int:
        """
        Count proteins in an annotation.

        Parameters
        ----------
        tag : str
            Annotation tag.

        Returns
        -------
        int
            Number of proteins.
        """
        

    @abstractmethod
    def get_protein_ids(self, tag: str) -> List[str]:
        """
        Get protein identifiers belonging to an annotation.

        Parameters
        ----------
        tag : str
            Annotation tag.

        Returns
        -------
        List[str]
            Protein identifiers.
        """
        

    @abstractmethod
    def isin(self, tag: str,  protein_ids: List[str]) -> pd.Series:
        """
        Checks if the give protein_ids are in the annotation by its tag.

        Parameters
        ----------
        tag : str
            Annotation tag.
        protein_ids : List[str]
            Protein identifiers to check.

        Returns
        -------
        pd.Series
            pandas Series with bools to indicate
            if the given protein_ids are present. 
            If the tag does not exists, and empty Series will be returned
        """
        

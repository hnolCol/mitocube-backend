from abc import ABC, abstractmethod
from typing import List, Optional, Dict
import pandas as pd

from config.models.annotations.annotations import ( AnnotationsModel, AnnotationGroupsModel)

class AnnotationGroupsABC(ABC):
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
    def insert(self, annotationgroup: AnnotationGroupsModel, user_tag: str) -> bool:
        """
        Create a new annotation group.

        Parameters
        ----------
        annotationgroup : AnnotationGroupsModel
            Annotation group data.

        Returns
        -------
        bool
            True if insert was successful
        """


    @abstractmethod
    def get(self, tag: str) -> AnnotationGroupsModel:
        """
        Gets the annotation group by tag.

        Parameters
        ----------
        tag : str
            Annotation group tag.

        Returns
        -------
        AnnotationGroupsModel
            The annotation group model.
        """


    @abstractmethod
    def find(self, search_string: Optional[str] = None, protein_tag: Optional[str] = None, search_in_annotations : bool = False, return_annotations : bool = False, limit : int = None) -> List[str]:
        """
        Finds all annotation groups.

        Parameters
        ----------
        search_string : Optional[str]
            Search string to filter annotation groups.
        protein_tag : Optional[str]
            Protein tag to filter annotation groups.    
        search_in_annotations : bool
            If True, search also in annotations linked to the groups.
        return_annotations : bool
            If True, return annotations linked to the groups. Will be returned. This is useful to get annotation groups along with their annotations. (e.g. searching for all)
        limit : int
            Limit the number of results.

        Returns
        -------
        List[str] | List[Dict]
            Annotation group tags.
            If return_annotations is True, a list of dicts with keys 'tag' and 'annotation_tags' is returned.
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
        

    @abstractmethod
    def count_annotations(self, group_tag: str) -> int:
        """
        Count annotations in a group.

        Parameters
        ----------
        group_tag : str
            Annotation group tag.

        Returns
        -------
        int
            Number of annotations.
        """
        
    @abstractmethod
    def edit_annotation_group(self, annotationgroup: AnnotationGroupsModel, user_tag: str) -> bool:
        """
        Update an existing annotation group.

        Parameters
        ----------
        annotationgroup : AnnotationGroupsModel
            Updated annotation group data.

        Returns
        -------
        bool
            True if update was successful.
        """

class AnnotationsABC(ABC):
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
    def insert(self, annotation: AnnotationsModel) -> bool:
        """
        Create a new annotation dataset and link protein identifiers.

        Parameters
        ----------
        annotation : AnnotationsModel
            Annotation data.

        Returns
        -------
        bool
            True if insert was successful.
        """
        

    @abstractmethod
    def get(self, tag: str) -> AnnotationsModel:
        """
        Gets annotation data by its tag.

        Parameters
        ----------
        tag : str
            Annotation tag.

        Returns
        -------
        AnnotationsModel
            Annotation data.
        """
        
    @abstractmethod
    def get_text(self, tag: str) -> str:
        """
        Get annotation text by its tag.
        """
    @abstractmethod
    def find(self, search_string: Optional[str] = None, group_tags: Optional[List[str]] = None,  protein_tags: Optional[List[str]] = None, submission_tags: Optional[List[str]] = None, limit: Optional[int] = None, group_by_group = False) -> List[str]:        
        """
        Find annotations.

        Parameters
        ----------
        search_string : Optional[str]
            Search string to filter annotation tags.
        group_tags : Optional[List[str]]
            Search within specific annotation groups
        protein_tags : Optional[List[str]]
            Search to annotations containing these proteins.
        submission_tags : Optional[List[str]]
            Search within specific submissions
        limit : Optional[int]
            Limit the number of results.
        group_by_group : bool
            If True, group results by their annotation group.
        Returns
        -------
        List[str]|List[dict]    
            Matching annotation tags. If group_by_group is True, a list of dicts with keys 'group_tag' and 'annotation_tags' is returned.
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
    def get_protein_tags(self, tag: str, submission_tag: Optional[str] = None) -> List[str]:
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
    def isin(self, tag: str, protein_tags: List[str]) -> pd.Series:
        """
        Checks if the give protein_tags are in the annotation by its tag.

        Parameters
        ----------
        tag : str
            Annotation tag.
        protein_tags : List[str]
            Protein identifiers to check.

        Returns
        -------
        pd.Series
            pandas Series with bools to indicate if the given protein_tags
            are present. If the tag does not exists, and empty Series
            will be returned
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
    def update_annotation(self, annotation: AnnotationsModel) -> bool:
        """
        Update an existing annotation.

        Parameters
        ----------
        group_tag : str
            Annotation group tag.
        tag : str
            Annotation tag.
        annotation : AnnotationsModel
            Updated annotation data.

        Returns
        -------
        bool
            True if update was successful.
        """

    @abstractmethod
    def delete_annotation(self, tag: str) -> bool:
        """
        Delete an annotation by its tag.

        Parameters
        ----------
        tag : str
            Annotation tag.

        Returns
        -------
        bool
            True if deletion was successful.
        """


    def get_proteins_by_annotation_group(self, group_tag: str, submission_tag: str) -> Dict[str, List[str]]:
        """
        Get all proteins for each annotation in a group, filtered by submission.
        Returns: {annotation_tag: [list of protein_tags]}
        """
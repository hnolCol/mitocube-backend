from __future__ import annotations

from abc import abstractmethod, ABC
# from datetime import timedelta
from typing import List, Dict, Optional, Tuple, Literal  # , Any
from deprecated import deprecated
import pandas as pd
from config.models.performance import QCPeptidesModel, QCRunModel, QCPeptideModel
from config.models.peptides import PeptideResponseModel
class PeptidesABC(ABC):
    """Abstract class to handle peptides.
    For peptides and proteins, instead of a random string as a tag, 
    we simply use the amino acid sequence. 
    """
    @abstractmethod
    def correlate_to(self, tag : str, min_size : int = 4, limit : int = None, filter_tag : str = None, exclude_within_protein_correlation : bool = True) -> pd.DataFrame:
        """Correlates a peptide to all other peptides based on their quantification data.
        
        Parameters
        ----------
        tag : str
            The tag of the peptide to correlate with others.
        min_size : int, optional
            Minimum size of the peptide quantification data to consider for correlation, by default 4.
        limit : int, optional
            Maximum number of results to return, by default None (no limit).
        filter_tag : str, optional
            If provided, only peptides of proteins that are part of the filter_tag will be considered for correlation.
        exclude_within_protein_correlation : bool, optional
            If True, excludes correlations between peptides of the same protein, by default True.

        Returns
        -------
        pd.DataFrame
            DataFrame containing the correlation results.
        """
        
    @abstractmethod
    def count(self, submission_tag : str = None) -> int:
        """Counts the number of peptides.

        Parameters
        ----------
        submission_tag : str, optional
            The tag of the submission to count peptides for. If None, counts all peptides, by default None.

        Returns
        -------
        int
            The number of peptides in the submission.
        """
    
    @abstractmethod
    def exists(self, tag : str) -> bool:
        """Checks if a given tag is associates with a peptide (e.g. sequence) 

        Parameters
        ----------
        tag : str
            The peptide sequence/tag 

        Returns
        -------
        bool
            If the tag is associated with a peptide 
        """
        
    @abstractmethod
    def find(self, search_string : str, submission_tag : str = None, limit : int = None, provide_protein_info : bool = False) -> List[str]|List[Tuple[str,List[str]]]:
        """Finds all peptides matching the search string.

        Parameters
        ----------
        search_string : str
            The search string to match against peptide sequences.
        submission_tag : str, optional
            If provided, only peptides associated/quantified in the given submission are returned, by default None
        limit : int, optional
            The maximum number of results to return. If None, all matching peptides are returned.
        provide_protein_info : bool, optional
            If True, returns a list of tuples with the peptide sequence and a list of associated protein tags, by default False.
        Returns
        -------
        List[str]|List[Tuple[str,List[str]]]
            A list of matching peptide tags (e.g. the sequence).
            If provide_protein_info is True, returns a list of tuples with the peptide sequence and a list of associated protein tags.
        """
        
        
    @abstractmethod
    def get(self, tag : str) -> PeptideResponseModel:
        """Returns a peptide by its tag (sequence).

        Parameters
        ----------
        tag : str
            The peptide tag (sequence).

        Returns
        -------
        PeptideResponseModel
            The peptide model.
        """
        
        
    @abstractmethod
    def get_abundance(self, tag : str, submission_tags : Optional[List[str]] = None) -> pd.DataFrame:
        """Retrieves the abundance of a peptide by its tag.

        Parameters
        ----------
        tag : str
            The tag of the peptide to retrieve.
        submission_tags : Optional[List[str]], optional
            A list of submission tags to filter the abundance data, by default None (all submissions).

        Returns
        -------
        pd.DataFrame
            The abundance data of the peptide.
        """     
    
    @abstractmethod
    def insert(self, protein_tags : List[str], peptide_sequence : str) -> bool:
        """Inserts a peptide into the database.

        Parameters
        ----------
        protein_tags : List[str]
            The tags of the proteins associated with the peptide.
        peptide_sequence : str
            The amino acid sequence of the peptide.

        Returns
        -------
        bool
            True if the insertion was successful, False otherwise.
        """
        pass

    
    @abstractmethod
    def is_quantified(self, peptide_tag : str) -> bool:
        """Checks if a peptide is quantified.

        Parameters
        ----------
        peptide_tag : str
            The tag of the peptide to check.

        Returns
        -------
        bool
            True if the peptide is quantified, False otherwise.
        """

    @abstractmethod
    def insert_quantification_data_from_df(self, submission_tag : str, sample_tag : str, quantification_data : pd.DataFrame) -> int:
        """Inserts quantification data for a multiple peptides.
        This method is used to insert quantification data for multiple peptides at once.
        The peptide tags are used as the index of the DataFrame. The peptide must be already present in the database and will 
        not be created if it does not exist, but simply skipped.
        
        Parameters
        ----------
        submission_tag : str
            The tag of the submission to which the quantification data belongs. If the submission does not exist, it will be skipped.
        sample_tag : str
            The tag of the sample to which the quantification data belongs. If the sample does not exist no data will be inserted.
        quantification_data : pd.DataFrame
            The quantification data to insert.

        Returns
        -------
        int
            The number of quantification entries inserted.
        """


    @abstractmethod
    def set_qc_peptides(self, peptides : QCPeptidesModel, join : bool = True):
        """"""
    
    # @abstractmethod
    # def get(self, tags : List[str] = None, limit : int = 10):
    #    ""
        
    # @abstractmethod
    # def insert(self) -> bool:
        
        
    # @abstractmethod
    # def delete(self, tag : str) -> bool:
    #     ""
    # @abstractmethod
    # def update(self, tag : str) -> bool:
        
    
    

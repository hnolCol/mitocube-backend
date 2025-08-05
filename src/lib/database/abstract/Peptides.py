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
    def find(self, search_string : str, limit : int = None) -> List[str]:
        """Finds all peptides matching the search string.

        Parameters
        ----------
        search_string : str
            The search string to match against peptide sequences.
        limit : int, optional
            The maximum number of results to return. If None, all matching peptides are returned.
        Returns
        -------
        List[str]
            A list of matching peptide tags (e.g. the sequence).
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
    def insert_quantification_data_from_df(self, submission_tag : str, quantification_data : pd.DataFrame) -> int:
        """Inserts quantification data for a multiple peptides.
        This method is used to insert quantification data for multiple peptides at once.
        The peptide tags are used as the index of the DataFrame. The peptide must be already present in the database and will 
        not be created if it does not exist, but simply skipped.
        
        Parameters
        ----------
        submission_tag : str
            The tag of the submission to which the quantification data belongs. If the submission does not exist, it will be skipped. 
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
        
    
    

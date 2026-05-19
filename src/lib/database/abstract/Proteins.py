from __future__ import annotations

from abc import abstractmethod, ABC
# from datetime import timedelta
from typing import List, Dict, Optional, Tuple, Literal  # , Any
from deprecated import deprecated
import pandas as pd
from config.models.performance import QCPeptidesModel, QCRunModel, QCPeptideModel
from config.models.peptides import PeptideResponseModel
from config.models.feature import FeatureNeoModel

class ProteinsABC(ABC):
    
    
    @abstractmethod
    def count(self, quantified: bool = True) -> int:
        """Returns the number of quantified proteins in the database

        Parameters
        ----------
        quantified : bool, optional
            If True, only counts proteins that have been quantified in at least one sample, by default True.

        Returns
        -------
        int
            The number of proteins in the database.
        """
    @abstractmethod
    def exists(self, tag: str) -> bool:
        """Checks if a protein with the given tag exists in the database.

        Parameters
        ----------
        tag : str
            The tag of the protein to check.

        Returns
        -------
        bool
            True if the protein exists, False otherwise.
        """
        
    @abstractmethod
    def find(self, search_string : str = None, submission_tags : List[str] = None, proteome_tags : List[str] = None, limit : int = 100) -> List[str]:
        """Finds proteins by a search string.

        Parameters
        ----------
        search_string : str, optional
            The search string to use for finding proteins.
        submission_tags : List[str], optional
            A list of submission tags to filter the proteins by (e.g. quantified in the given submission). If None, does not filter by submission tags, by default None.
        proteome_tags : List[str], optional
            A list of proteome tags to filter the proteins by. If None, does not filter by proteome tags, by default None.
        limit : int, optional
            The maximum number of results to return, by default 100.

        Returns
        -------
        List[str]
            A list of protein tags that match the search string.
        """

    @abstractmethod
    def get(self, tag : str) -> FeatureNeoModel:
        """Retrieves a protein by its tag.

        Parameters
        ----------
        tag : str
            The tag of the protein to retrieve.

        Returns
        -------
        FeatureNeoModel
            The protein model.
        """
        
    @abstractmethod
    def get_gene_name(self, tag : str) -> str:
        """Retrieves the gene name of a protein by its tag.

        Parameters
        ----------
        tag : str
            The tag of the protein to retrieve the gene name for.

        Returns
        -------
        str
            The gene name of the protein
        """
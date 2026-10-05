from __future__ import annotations

from abc import abstractmethod, ABC
from typing import List, Tuple
import pandas as pd

from config.models.precursors import PrecursorResponseModel


class PrecursorsABC(ABC):
    """Abstract class to handle precursors.
    Precursors are the charge-state specific counterparts of peptides. Hence, a peptide
    can have multiple precursors (e.g. one for charge 2 and one for charge 3). 
    The precursor tag is the peptide sequence followed by the charge state separated by a dot, e.g. PEPTIDEK.2.
    Each precursor is associated with a protein group tag. 
    """

    @abstractmethod
    def count(self, submission_tag: str = None) -> int:
        """Counts the number of precursors.

        Parameters
        ----------
        submission_tag : str, optional
            The tag of the submission to count precursors for. If None, counts all precursors, by default None.

        Returns
        -------
        int
            The number of precursors in the submission.
        """

    @abstractmethod
    def exists(self, tag: str) -> bool:
        """Checks if a given tag is associated with a precursor (e.g. SEQUENCE.CHARGE).

        Parameters
        ----------
        tag : str
            The precursor tag (sequence followed by the charge state).

        Returns
        -------
        bool
            If the tag is associated with a precursor.
        """

    @abstractmethod
    def find(self, search_string: str, submission_tag: str = None, limit: int = None, provide_protein_info: bool = False) -> List[str] | List[Tuple[str, List[str]]]:
        """Finds all precursors matching the search string.

        Parameters
        ----------
        search_string : str
            The search string to match against precursor tags (sequence followed by charge state).
        submission_tag : str, optional
            If provided, only precursors associated/quantified in the given submission are returned, by default None.
        limit : int, optional
            The maximum number of results to return. If None, all matching precursors are returned.
        provide_protein_info : bool, optional
            If True, returns a list of tuples with the precursor tag and a list of associated protein group tags, by default False.

        Returns
        -------
        List[str] | List[Tuple[str, List[str]]]
            A list of matching precursor tags.
            If provide_protein_info is True, returns a list of tuples with the precursor tag and a list of associated protein group tags.
        """

    @abstractmethod
    def get(self, tag: str) -> PrecursorResponseModel:
        """Returns a precursor by its tag (sequence.charge).

        Parameters
        ----------
        tag : str
            The precursor tag (sequence followed by the charge state).

        Returns
        -------
        PrecursorResponseModel
            The precursor model.
        """

    @abstractmethod
    def get_abundance(self, tag: str, submission_tags: List[str] = None) -> pd.DataFrame:
        """Retrieves the abundance of a precursor by its tag.

        Parameters
        ----------
        tag : str
            The tag of the precursor to retrieve.
        submission_tags : List[str], optional
            A list of submission tags to filter the abundance data, by default None (all submissions).

        Returns
        -------
        pd.DataFrame
            The abundance data of the precursor.
        """

    @abstractmethod
    def insert(self, protein_group_tag: str, peptide_sequence: str, charge: int) -> bool:
        """Inserts a precursor into the database. The precursor tag is derived from the
        peptide sequence and the charge state (sequence.charge). The precursor is connected
        to the given protein group. If the precursor already exists, it is merged and the
        protein group association is added.

        Parameters
        ----------
        protein_group_tag : str
            The tag of the protein group associated with the precursor.
        peptide_sequence : str
            The amino acid sequence of the peptide underlying the precursor.
        charge : int
            The charge state of the precursor.

        Returns
        -------
        bool
            True if the insertion was successful, False otherwise.
        """

    @abstractmethod
    def is_quantified(self, precursor_tag: str) -> bool:
        """Checks if a precursor is quantified.

        Parameters
        ----------
        precursor_tag : str
            The tag of the precursor to check.

        Returns
        -------
        bool
            True if the precursor is quantified, False otherwise.
        """

    @abstractmethod
    def insert_quantification_data_from_df(self, submission_tag: str, sample_tag: str, quantification_data: pd.DataFrame) -> int:
        """Inserts quantification data for multiple precursors.
        This method is used to insert quantification data for multiple precursors at once.
        The precursor tags are used as the index of the DataFrame. The precursor must be already present in the database and will
        not be created if it does not exist, but simply skipped.

        Parameters
        ----------
        submission_tag : str
            The tag of the submission to which the quantification data belongs. If the submission does not exist, it will be skipped.
        sample_tag : str
            The tag of the sample to which the quantification data belongs. If the sample does not exist no data will be inserted.
        quantification_data : pd.DataFrame
            The quantification data to insert. Requires the columns 'tag' (precursor tag) and 'value'.
            Optional columns are 'score' and 'retention_time'.

        Returns
        -------
        int
            The number of quantification entries inserted.
        """

from __future__ import annotations

from abc import abstractmethod, ABC
from typing import List, Tuple
import pandas as pd

from config.models.precursors import PrecursorInsertModel, PrecursorResponseModel


class PrecursorsABC(ABC):
    """Abstract class to handle precursors.
    Precursors are the charge-state specific counterparts of peptides. Hence, a peptide
    can have multiple precursors (e.g. one for charge 2 and one for charge 3). 
    The precursor tag is the peptide sequence followed by the charge state separated by a dot, e.g. PEPTIDEK.2.
    Each precursor is associated with one or multiple protein group tags. 
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
    def count_by_protein_group(self, protein_group_tag: str, submission_tag: str = None) -> int:
        """Counts the number of precursors associated with a given protein group.

        Parameters
        ----------
        protein_group_tag : str
            The tag of the protein group to count precursors for.
        submission_tag : str, optional
            If provided, only precursors quantified in the given submission are counted, by default None.

        Returns
        -------
        int
            The number of precursors associated with the protein group.
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
    def find(self, search_string: Optional[str] = None, submission_tag: str = None, limit: int = None, provide_protein_info: bool = False) -> List[str] | List[Tuple[str, List[str]]]:
        """Finds all precursors matching the search string.

        Parameters
        ----------
        search_string : str, optional
            The search string to match against precursor tags (sequence followed by charge state). If None, the first precursor tags up to the limit are returned, by default None.
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
        """Returns a precursor by its tag (sequence.charge). The protein_group_tag is the protein group
        associated with the precursor that has the least proteins connected to itself (e.g. the protein group
        consisting of a single protein). All associated protein groups are returned in protein_group_tags.

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
    def get_by_protein_group(self, protein_group_tag: str, submission_tag: str = None, limit: int = None) -> List[PrecursorResponseModel]:
        """Returns all precursors associated with a given protein group.

        Parameters
        ----------
        protein_group_tag : str
            The tag of the protein group to retrieve precursors for.
        submission_tag : str, optional
            If provided, only precursors quantified in the given submission are returned, by default None.
        limit : int, optional
            The maximum number of results to return. If None, all precursors are returned.

        Returns
        -------
        List[PrecursorResponseModel]
            The precursor models associated with the protein group.
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
    def insert(self, protein_group_tags: List[str], peptide_sequence: str, charge: int, mz: float = None, im: float = None) -> bool:
        """Inserts a precursor into the database. The precursor tag is derived from the
        peptide sequence and the charge state (sequence.charge). The precursor is connected
        to the given protein groups. If the precursor already exists, it is merged and the
        protein group associations are added.

        Parameters
        ----------
        protein_group_tags : List[str]
            The tags of the protein groups associated with the precursor.
        peptide_sequence : str
            The amino acid sequence of the peptide underlying the precursor.
        charge : int
            The charge state of the precursor.
        mz : float, optional
            The mass-to-charge ratio of the precursor, by default None.
        im : float, optional
            The ion mobility value of the precursor (e.g. from timsTOF instruments), by default None.

        Returns
        -------
        bool
            True if the insertion was successful, False otherwise.
        """

    @abstractmethod
    def bulk_insert(self, precursors: List[PrecursorInsertModel], batch_size: int = 1000, transaction_batch_size: int = 400) -> int:
        """Bulk inserts a list of precursors into the database. The precursor tags are derived from the
        peptide sequence and the charge state (sequence.charge). The precursors are connected
        to their respective protein groups. Precursors that already exist are merged.
        
        The input is chunked on the client side (batch_size) and each chunk is inserted using a 
        CALL { ... } IN TRANSACTIONS subquery so that Neo4J commits the insert in smaller 
        transactions (transaction_batch_size), avoiding memory errors for large inputs 
        (e.g. 90K precursors per sample). 

        Parameters
        ----------
        precursors : List[PrecursorInsertModel]
            The precursors to insert.
        batch_size : int, optional
            The number of precursors sent to the database per query, by default 1000
        transaction_batch_size : int, optional
            The number of rows per internal transaction (IN TRANSACTIONS OF ... ROWS), by default 400

        Returns
        -------
        int
            The number of inserted precursors.
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

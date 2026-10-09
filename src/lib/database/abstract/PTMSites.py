from __future__ import annotations
from abc import abstractmethod, ABC
from typing import List, Dict, Optional
import pandas as pd
from config.models.ptms import PTMSiteInsertModel, PTMSiteResponseModel


class PTMSitesABC(ABC):
    """
    Abstract class to handle post translational modification (PTM) sites.
    A PTM site is a modification at a specific position of a protein, e.g. the
    phosphorylation of serine 473 in AKT1. The tag is derived and validated from the
    protein tag (or the protein group tag for group level identifications), the position
    and the modification, e.g. P12345_S473_PHOSPHO.
    A site is linked to the protein group it was identified in via [:OF_PROTEIN_GROUP]
    and is supported by one or multiple modified precursors via [:SUPPORTED_BY].
    Sites are quantified per sample via a [:QUANTIFIED] relationship that carries the
    value (log2 intensity), the score and the site_localization (localization probability).
    """

    @abstractmethod
    def count(self, submission_tag : str = None) -> int:
        """
        Counts the number of PTM sites, optionally within a submission.
        """

    @abstractmethod
    def exists(self, tag : str) -> bool:
        """
        Checks if a tag is associated with a PTM site.
        """

    @abstractmethod
    def find(self, search_string : Optional[str] = None, submission_tag : str = None, limit : int = None) -> List[str]:
        """
        Finds all PTM sites matching the search string, optionally within a submission. If the search string is None, the first PTM site tags up to the limit are returned.
        """

    @abstractmethod
    def get(self, tag : str) -> PTMSiteResponseModel:
        """
        Returns a PTM site by its tag.
        """

    @abstractmethod
    def insert(self, ptm_site : PTMSiteInsertModel) -> bool:
        """
        Inserts a PTM site into the database. The site is linked to the protein group
        via [:OF_PROTEIN_GROUP] and to the supporting precursors via [:SUPPORTED_BY].
        Existing tags are merged.
        """

    @abstractmethod
    def bulk_insert(self, ptm_sites : List[PTMSiteInsertModel], batch_size : int = 1000, transaction_batch_size : int = 400) -> Dict:
        """
        Bulk inserts PTM sites. Like the precursor bulk insert this is a library level
        entity insert, the per submission/sample quantification is inserted separately via
        insert_quantification_data_from_df.
        Sites whose protein group does not exist are skipped and reported as not_found.
        Supporting precursors that do not exist are skipped and reported as
        precursor_links_not_created.

        Returns
        -------
        Dict
            A report with the number of inserted sites (valid), skipped sites (not_found)
            and skipped precursor links (precursor_links_not_created).
        """

    @abstractmethod
    def is_quantified(self, tag : str) -> bool:
        """
        Checks if a PTM site is quantified.
        """

    @abstractmethod
    def get_abundance(self, tag : str, submission_tags : List[str] = None) -> pd.DataFrame:
        """
        Retrieves the abundance of a PTM site by its tag, optionally filtered by submissions.
        """

    @abstractmethod
    def insert_quantification_data_from_df(self, submission_tag : str, sample_tag : str, quantification_data : pd.DataFrame) -> int:
        """
        Inserts quantification data for PTM sites. The DataFrame requires the columns
        'tag' (PTM site tag) and 'value'. Optional columns are 'score' and
        'site_localization'. Sites that do not exist are skipped.
        """

from abc import abstractmethod, ABC 
from typing import List 

from config.models.performance import QCRunModel, QCStandardModel, QCPrecursorModel, QCPrecursorsModel


class QCABC(ABC):
    def __init__(self) -> None:
        ""
        
    @abstractmethod
    def exists(self, tag : str) -> bool: 
        """Checks if a tag is associated with a performance run 

        Parameters
        ----------
        tag : str
            The performance run tag 

        Returns
        -------
        bool
            If the given tag is associated with a performance run. 
        """
            
    @abstractmethod
    def count(self, by_instrument : bool = False) -> int:
        """Counts the number of performance runs. 
        
        Parameters
        ----------
        by_instrument : bool, optional
            If true the number of performance runs is counted by
            the instrument., by default False

        Returns
        -------
        int
            _description_
        """
    
    @abstractmethod
    def get(self, tags : List[str] = None, instrument : str = None, limit : int = 50) -> QCRunModel:
        """Returns the perfromance run. 

        Parameters
        ----------
        tags : List[str], optional
            _description_, by default None
        instrument : str, optional
            _description_, by default None
        limit : int, optional
            _description_, by default 50

        Returns
        -------
        QCRunModel
            _description_
        """
    
    @abstractmethod
    def insert(self, performance_run : QCRunModel) -> bool: 
        """Add a new performance run to the database 

        Parameters
        ----------
        performance_run : QCRunModel
            _description_

        Returns
        -------
        bool
            _description_
        """
        
    @abstractmethod
    def delete(self, tag : str) -> bool:
        """Deletes a performance 

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
    def update(self, tag : str, peformance_run : QCRunModel) -> bool:
        """Updates a specific performance run. 

        Parameters
        ----------
        tag : str
            _description_
        peformance_run : QCRunModel
            _description_

        Returns
        -------
        bool
            _description_
        """

    @abstractmethod
    def standard_exists(self, tag : str) -> bool:
        """
        Checks if a tag is associated with a QC standard (e.g. HeLa digest, BSA).

        Parameters
        ----------
        tag : str
            The QC standard tag.

        Returns
        -------
        bool
            If the given tag is associated with a QC standard.
        """

    @abstractmethod
    def get_standards(self, type : str = None, vendor : str = None) -> List[QCStandardModel]:
        """
        Returns the QC standards, optionally filtered by type and vendor.

        Parameters
        ----------
        type : str, optional
            The type of the standard (Cell lysate, Protein), by default None.
        vendor : str, optional
            The vendor of the standard, by default None.

        Returns
        -------
        List[QCStandardModel]
            The QC standards.
        """

    @abstractmethod
    def insert_standard(self, standard : QCStandardModel) -> bool:
        """
        Adds a new QC standard to the database. Standards are immutable,
        an existing tag is merged.

        Parameters
        ----------
        standard : QCStandardModel
            The standard to add.

        Returns
        -------
        bool
            True if the standard was added, False otherwise.
        """

    @abstractmethod
    def delete_standard(self, tag : str) -> bool:
        """
        Deletes a QC standard. A standard can only be deleted if no QC run
        is linked to it.

        Parameters
        ----------
        tag : str
            The tag of the standard to delete.

        Returns
        -------
        bool
            True if the standard was deleted, False if it does not exist or is still in use.
        """

    @abstractmethod
    def insert_qc_precursors(self, run_tag : str, precursors : List[QCPrecursorModel]) -> bool:
        """
        Adds the quantified QCPrecursors to a QC run. Only a specific subset of precursors
        is recorded for QC, the full quantification data is not uploaded. Precursors that
        do not exist in the database are skipped.

        Parameters
        ----------
        run_tag : str
            The tag of the QC run the precursors belong to.
        precursors : List[QCPrecursorModel]
            The precursors with their value, score and retention time.

        Returns
        -------
        bool
            True if the precursors were added, False if the run does not exist.
        """

    @abstractmethod
    def get_qc_precursors(self, run_tag : str) -> List[QCPrecursorModel]:
        """
        Returns the QCPrecursors that were recorded for a QC run.

        Parameters
        ----------
        run_tag : str
            The tag of the QC run.

        Returns
        -------
        List[QCPrecursorModel]
            The recorded precursors of the run.
        """

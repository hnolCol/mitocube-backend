from abc import abstractmethod, ABC 
from typing import List 

from config.models.performance import QCRunModel


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
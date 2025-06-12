from abc import abstractmethod, ABC 
from typing import List 

from config.models.performance import QCRunModel


class SamplesABC(ABC):
    def __init__(self) -> None:
        ""
        
    @abstractmethod
    def exists(self, tag : str) -> bool: 
        """Checks if a tag is associated with sample 

        Parameters
        ----------
        tag : str
            The sample run tag 

        Returns
        -------
        bool
            If the given tag is associated with a sample. 
        """
        
    @abstractmethod
    def get_sample(tag : str):
        ""
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
    def insert(self, submission_tag : str, sample_name : str, sample_index : int) -> str:
        """Inserts a sample into the database.
        The tag will be generated automatically as a random UUID.
        Parameters
        ----------
        submission_tag : str
            The submission tag associated with the sample.
        sample_name : str
            The name of the sample.
        sample_index : int
            The index of the sample in the submission.
        
        Returns
        -------
        str
            The generated sample tag.
        """
        
    
    @abstractmethod
    def get_sample(tag : str):
        ""
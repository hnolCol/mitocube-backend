from abc import abstractmethod, ABC 
from typing import List 

from config.models.conditions_applications import ConditionApplicationAttributeModel
from config.models.samples import SampleModel

class SamplesABC(ABC):
    def __init__(self) -> None:
        ""
        
        
    @abstractmethod
    def get(self, tag : str) -> SampleModel:
        "Returns the sample information for a given sample tag."
        
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
    def get_sample(tag : str) -> SampleModel:
        ""
        
    @abstractmethod
    def get_condition_procedure(self, tag: str, group_by_attribute : bool = False) -> List[str]|List[ConditionApplicationAttributeModel]:
        """Get all condition procedures for a given sample. If no sample tag is provided, all condition procedures are returned.
        You may also sort the results by the most frequent condition procedures.
        If only one tag is found, a single string is returned. If no tag is found, an empty list is returned. 
        
        Parameters
        ----------
        tag : str
            The tag of the sample to get the condition procedures for.
        group_by_attribute : bool, optional
            If True, the results are grouped by attribute and returned as a list of ConditionApplicationAttribute
            
        Returns
        -------
        List[str]|str
            A list of condition procedure tags. If only a single tag is found, a single string is returned.
            If no tag is found, an empty list is returned.
        """
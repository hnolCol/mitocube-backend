from __future__ import annotations
from abc import abstractmethod, ABC

from typing import List, Literal, Dict
from deprecated import deprecated



class InvestigationABC(ABC):

    @abstractmethod
    def exists(self, tag : str) -> bool:
        """Checks if the maintenance event exists. 

        Parameters
        ----------
        tag : str
            _description_

        Returns
        -------
        bool
            If the given tag is associated with an investigation
        """
        
    @abstractmethod
    def link(self, tag : str, study_tag : str, user_tag : str, created_at : float):
        """Links a study tag to an investigation. 

        Parameters
        ----------
        tag : str
            The investigation tag
        study_tag : str
            The study tag
        user_tag : str
            The tag of the user who created the link.
        created_at : float
            Timestamp when the link has been created
        """

    @abstractmethod
    def get(self, tag : str):
        """Returns investigation by its tag. 

        Parameters
        ----------
        tag : str
            List of investigations to retrieve from the database. 
            If a tag does not exists, it is simply ignored. 
        """

    
    @abstractmethod
    def get_studies(self, tag : str) -> List[str]:
        """Returns the tags of the studies within the investigation
        following the ISA model structure."""
        
    
    @abstractmethod
    def insert(self, investigation : Dict):
        "Insert a new investigation. "
        
        
    @abstractmethod
    def delete(self, tag : str) -> bool:
        "Deletes an investigation."
        


        

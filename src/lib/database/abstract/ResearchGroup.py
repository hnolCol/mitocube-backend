from abc import abstractmethod, ABC 
from typing import List, Dict 

from config.models.researchgroup import ResearchGroupModel


class ResearchGroupABC(ABC):
    def __init__(self) -> None:
        ""
        
    @abstractmethod  
    def insert_users(self, tag : str, user_tags : List[str]):
        " "
    @abstractmethod
    def exists(self, tag : str) -> bool:
        "" 
    @abstractmethod
    def get(self, tag : str) -> ResearchGroupModel:
        ""
    @abstractmethod
    def get_users_count(self, tag : str) -> int:
        " "
    @abstractmethod
    def get_submission_tags(self, tags : str) -> List[str]:
        "Returns the submission tags associated with the research group"
        
    @abstractmethod
    def get_submissions_count(self, tag : str) -> int:
        ""
    @abstractmethod
    def get_samples_count(self, tag : str) -> int:
        "Returns the number of samples associated with the research group"
        
    @abstractmethod    
    def insert(self, research_group):
        "" 
        
        
    @abstractmethod
    def delete(self, tag : str) -> bool:
        "" 
        
        
    @abstractmethod 
    def update(self) -> Dict:
        "" 
        
    @abstractmethod
    def find(self, search_string: str = None, user_tags: List[str] = None, submission_tags: List[str] = None, limit: int = 20) -> List[str]:
        """Finds research group tags that match the search string, user tags, or submission tags."""
        
    @abstractmethod
    def get_heads(self, tag : str) -> List[str]:
        "Returns the user tags of the research group heads (PIs) of the given research group"

    @abstractmethod
    def is_head(self, user_tag : str, group_tag : str = None) -> bool:
        "Checks if the user is a head (PI) of the given research group. If no group tag is given, checks if the user is a head of any research group."

    @abstractmethod
    def set_head(self, group_tag : str, user_tag : str):
        "Makes the user a head (PI) of the research group"

    @abstractmethod
    def remove_head(self, group_tag : str, user_tag : str):
        "Removes the user as head (PI) of the research group"

    @abstractmethod
    def set_subgroup(self, parent_tag : str, child_tag : str):
        "Defines a parent-child relationship between two research groups, where the child group is a subgroup of the parent group."
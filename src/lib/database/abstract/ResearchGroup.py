from abc import abstractmethod, ABC 
from typing import List, Dict 

from config.models.researchgroup import ResearchGroupModel


class ResearchGroupABC(ABC):
    def __init__(self) -> None:
        ""
        
    @abstractmethod  
    def add_users(self, tag : str, user_tags : List[str]):
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
        

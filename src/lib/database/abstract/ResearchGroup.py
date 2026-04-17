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
    def get_submissions_count(self, tag : str) -> int:
        ""
        
    @abstractmethod    
    def insert(self, research_group):
        "" 
        
        
    @abstractmethod
    def delete(self, tag : str) -> bool:
        "" 
        
        
    @abstractmethod 
    def update(self) -> Dict:
        "" 
        
        
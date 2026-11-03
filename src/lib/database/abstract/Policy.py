from abc import ABC, abstractmethod
from typing import List, Optional
from config.models.Policy import PolicyModel, PolicyInsertModel, PolicyUpdateModel, PolicyStatusModel, PolicyVersionModel


class PolicyABC(ABC):

    @abstractmethod
    def list(self) -> List[PolicyModel]: 
        ""
    @abstractmethod
    def get(self, tag : str) -> Optional[PolicyModel]: 
        ""
    @abstractmethod
    def history(self, tag : str) -> List[PolicyVersionModel]: 
        ""
    @abstractmethod
    def create(self, policy : PolicyInsertModel, user_tag : str) -> PolicyModel: 
        ""
    @abstractmethod
    def update(self, tag : str, policy : PolicyUpdateModel, user_tag : str) -> Optional[PolicyModel]: 
        ""
    @abstractmethod
    def delete(self, tag : str) -> bool: 
        ""
    @abstractmethod
    def agree(self, tag : str, user_tag : str) -> bool: 
        ""
    @abstractmethod
    def get_status(self, user_tag : str) -> List[PolicyStatusModel]: 
        ""
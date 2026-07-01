from abc import ABC, abstractmethod
from typing import List
from config.models.diseases import DiseaseModel, DiseaseInputModel

class DiseaseABC(ABC):

    @abstractmethod
    def count(self) -> int:
        "Returns the total number of diseases in the database."
        
    @abstractmethod
    def exists(self, tag: str) -> bool:
        "Checks if a disease with the given tag exists in the database."

    @abstractmethod
    def insert(self, disease: DiseaseInputModel, user_tag: str) -> bool:
        "Inserts a new disease into the database. Returns True if successful, False otherwise."

    @abstractmethod
    def get(self, tags: List[str] = None, limit: int = 20) -> List[DiseaseModel]:
        "Retrieves diseases from the database. If tags are provided, retrieves diseases matching those tags. Otherwise, retrieves all diseases up to the specified limit."

    @abstractmethod
    def find(self, query: str = "", limit: int = 20) -> List[DiseaseModel]:
        "Searches for diseases in the database that match the given query string. Returns a list of matching diseases up to the specified limit."

    @abstractmethod
    def delete(self, tag: str, is_active: bool = False) -> bool: 
        "Deletes a disease from the database. If is_active is True, performs a soft delete (e.g., marks the disease as inactive). If False, performs a hard delete. Returns True if successful, False otherwise."
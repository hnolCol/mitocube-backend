from abc import ABC, abstractmethod
from typing import List, Optional
from config.models.crosslink import CrosslinkInsertModel

class CrosslinkABC(ABC):

    @abstractmethod
    def exists(self, tag: str) -> bool:
        """Checks if an XL exists."""
       

    @abstractmethod
    def insert(self, data: CrosslinkInsertModel, user_tag: str) -> bool:
        """Inserts a new XL created by a user. Returns True if successful, False otherwise."""
       

    @abstractmethod
    def insert_external(self, data: CrosslinkInsertModel, resource_tag: str) -> bool:
        """Inserts an XL sourced from an external resource (e.g. a publication).
        Returns True if successful, False if the resource or either protein doesn't exist."""
       

    @abstractmethod
    def get(self, tag: str) -> dict:
        """Returns an XL by its tag, including source info if linked to an ExternalResource."""
       

    @abstractmethod
    def find(self, protein_tag: str, resource_tag: Optional[str] = None, limit: Optional[int] = None) -> List[dict]:
        """Returns XLs involving the given protein, optionally filtered by external resource."""
    

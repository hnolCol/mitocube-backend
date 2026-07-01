from abc import ABC, abstractmethod
from typing import List, Optional
from config.models.external_resource import ExternalResourceInsertModel, ExternalResourceModel


class ExternalResourceABC(ABC):

    @abstractmethod
    def exists(self, tag: str) -> bool:
        """Checks if an external resource exists."""
        

    @abstractmethod
    def insert(self, data: ExternalResourceInsertModel) -> bool:
        """Inserts a new external resource (e.g. a publication). Returns True if successful."""
        

    @abstractmethod
    def get(self, tag: str) -> ExternalResourceModel:
        """Returns an external resource by its tag."""
        

    @abstractmethod
    def find(self, limit: Optional[int] = None) -> List[str]:
        """Returns tags of all external resources."""
        

    @abstractmethod
    def link_crosslink(self, resource_tag: str, crosslink_tag: str) -> bool:
        """Links an existing crosslink to an external resource via HAS_XL."""
        

    @abstractmethod
    def find_crosslinks(self, resource_tag: str, limit: int = 100) -> List[dict]:
        """Returns crosslinks linked to an external resource."""
        

    @abstractmethod
    def find_by_protein(self, protein_tag: str) -> List[dict]:
        """Returns external resources that have crosslink annotations for a given protein."""
        
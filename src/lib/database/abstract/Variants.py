from abc import ABC, abstractmethod
from typing import List
from config.models.variants import VariantModel, VariantInputModel

class VariantABC(ABC):

    @abstractmethod
    def count(self) -> int:
        "Returns the total number of variants in the database."

    @abstractmethod
    def exists(self, tag: str) -> bool:
        "Checks if a variant with the given tag exists in the database."

    @abstractmethod
    def insert(self, variant: VariantInputModel, user_tag: str) -> bool:
        "Inserts a new variant into the database. Returns True if successful, False otherwise."

    @abstractmethod
    def get(self, tag: str) -> VariantModel | None:
        "Retrieves a variant from the database by its tag. Returns the variant if found, or None if not found."

    @abstractmethod
    def find_by_protein(self, protein_tag: str, limit: int = 20) -> List[VariantModel]:
        "Searches for variants in the database that are associated with the given protein tag. Returns a list of matching variants up to the specified limit."

    @abstractmethod
    def find_by_disease(self, disease_tag: str, limit: int = 20) -> List[VariantModel]:
        "Searches for variants in the database that are associated with the given disease tag. Returns a list of matching variants up to the specified limit."

    @abstractmethod
    def delete(self, tag: str, is_active: bool = False) -> bool:
        "Deletes a variant from the database. If is_active is True, performs a soft delete (e.g., marks the variant as inactive). If False, performs a hard delete. Returns True if successful, False otherwise."
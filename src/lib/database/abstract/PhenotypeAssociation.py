from abc import ABC, abstractmethod
from typing import List
from config.models.PhenotypeAssociation import PhenotypeAssociationModel, PhenotypeAssociationInputModel

class PhenotypeAssociationABC(ABC):

    @abstractmethod
    def count(self) -> int:
        "Returns the total number of phenotype associations in the database."

    @abstractmethod
    def exists(self, tag: str) -> bool:
        "Checks if a phenotype association with the given tag exists in the database."

    @abstractmethod
    def insert(self, data: PhenotypeAssociationInputModel, user_tag: str) -> str:
        "Inserts a new phenotype association into the database. Returns the tag of the newly created association if successful, or an empty string if the insertion failed."

    @abstractmethod
    def get(self, tag: str) -> PhenotypeAssociationModel | None: 
        "Retrieves a phenotype association from the database by its tag. Returns the association if found, or None if not found."

    @abstractmethod
    def find(self, query: str = "", limit: int = 20) -> List[str]:
        "Searches for phenotype associations in the database that match the given query string. Returns a list of matching association tags up to the specified limit."

    @abstractmethod
    def find_by_phenotype(self, phenotype_tag: str, limit: int = 20) -> List[str]: 
        "Searches for phenotype associations in the database that are associated with the given phenotype tag. Returns a list of matching association tags up to the specified limit."

    @abstractmethod
    def find_by_disease(self, disease_tag: str, limit: int = 20) -> List[str]: 
        "Searches for phenotype associations in the database that are associated with the given disease tag. Returns a list of matching association tags up to the specified limit."

    @abstractmethod
    def delete(self, tag: str, is_active: bool = False) -> bool: 
        "Deletes a phenotype association from the database. If is_active is True, performs a soft delete (e.g., marks the association as inactive). If False, performs a hard delete. Returns True if successful, False otherwise."

    @abstractmethod
    def find_by_protein(self, protein_tag: str, limit: int = 20) -> List[str]:
        "Returns phenotype association tags linked to a given protein."

    @abstractmethod
    def find_by_genotype(self, genotype_tag: str, limit: int = 20) -> List[str]:
        "Returns phenotype association tags linked to a given genotype."
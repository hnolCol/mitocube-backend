from abc import ABC, abstractmethod
from typing import List, Dict

class GeneticApplicationsABC(ABC):
    "Gene application database abstract class. A genotype "
    
    
    @abstractmethod
    def get(self, tag : str) -> Dict:
        """Gets a genetic application by its tag.

        Parameters
        ----------
        tag : str
            The tag of the genetic application.

        Returns
        -------
        Dict
            The genetic application data.
        """
        
    
    @abstractmethod
    def insert(self, gene_application : Dict) -> int:
        """Inserts a gene application into the database.

        Parameters
        ----------
        gene_application : Dict
            The gene application data.

        Returns
        -------
        int
            The ID of the inserted gene application.
        """

from __future__ import annotations
from abc import abstractmethod, ABC

from config.models.phenotype import PhenotypeGenotypeInput, PhenotypeModel, PhenotypeInputModel

from typing import List, Dict, Optional, Tuple

import pandas as pd



    
class PhenotypeABC(ABC):
    
    
    @abstractmethod
    def count(self) -> int:
        """Counts the number of phenotypes in the database. 

        Returns
        -------
        int
            _description_
        """
    
    @abstractmethod
    def insert(self, phenotype : PhenotypeInputModel) -> bool:
        "Inserts a phenotype to the database"
    
    
    @abstractmethod
    def get(self, tags : List[str] = None, limit : int = 20) -> List[PhenotypeModel]:
        """Returns the phenotypes in the database 
        If tag is None, all phenotypes ($limit) will
        be returned

        Parameters
        ----------
        tags : List[str], optional
            _description_, by default None
        limit : int
            The maximum number of phenotypes to return, default 20
        Returns
        -------
        List[PhenotypeModel]
        """
        
    @abstractmethod
    def find(self, query : str = None, limit : int = 20) -> List[PhenotypeModel]:
        """Finds phenotypes by a query. 

        Parameters
        ----------
        query : str, optional
            The search query, by default None
        limit : int, optional
            The limit of phenotypes returned, by default 20

        Returns
        -------
        List[PhenotypeModel]
            The phenotype models matching the query. 
        """
        
        
    @abstractmethod
    def connect(self, tag : str, genotype_tag, attributes : Dict[str,List[str]]):
        """Connect a genotype and a phenotype.

        Parameters
        ----------
        tag : str
            _description_
        genotype_tag : _type_
            _description_
        attributes : Dict[str,List[str]]
            _description_
        """
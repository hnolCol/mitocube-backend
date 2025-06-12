from abc import abstractmethod, ABC
from typing import List 
from neo4j import Driver

from config.models.genotype import MinimalGenotypeModel, GenotypeModel 


class GenotypeABC(ABC):
    """
    Database class  that handles the genotypes. """
    
    def __init__(self, driver : Driver) -> None:

        self._driver = driver 
        
        
    @abstractmethod
    def add(self, genotype : GenotypeModel, user_tag : str):
        """Adds a genotype to the database. 

        Parameters
        ----------
        genotype : GenotypeModel
            _description_
        user_tag : str
            _description_
        """
        
        
    @abstractmethod
    def get(self, tags : List[str] = None, proteome_tags : List[str] = None, protein_tags : List[str] = None) -> List[MinimalGenotypeModel]:
        """Returns the genotypes by the tags. 
        If tag is None (default) all genotypes will be returned. 

        Parameters
        ----------
        tags : List[str], optional
            The list of genotype tags that should be returned, by default None
        proteome_tags : List[str], optional
            The proteome_ids to consider when return the genotype, by default None
        protein_tags : List[str], optional
            The protein tags (Uniprot IDs). Provide a list of tags to get 
            all the genotypes that effect the given gene coding sequence, by default None

        Returns
        -------
        List[MinimalGenotypeModel]
            _description_
        """
        
    
        
    def find(self, query : str) -> List[MinimalGenotypeModel]:
        #TEST!! 
        query_string = query.lower() 
        query = (
            "MATCH (g:Genotype) "
            "WHERE g.s CONTAINS $query_string "
            "RETURN g.tag as tag, g.text as text, g.proteome_id as proteome_id "
        )
        
        r, _ , _= self._driver.execute_query(query, query_string = query_string, routing_="r", database_="neo4j")
        return [MinimalGenotypeModel(**ri.data()) for ri in r]
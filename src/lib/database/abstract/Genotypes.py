from abc import abstractmethod, ABC
from typing import List 
from neo4j import Driver

from config.models.genotype import MinimalGenotypeModel, GenotypeModel , InsertGeneticApplicationModel
from config.models.attributes import AttributeTree

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
    def get(self, tag) -> List[MinimalGenotypeModel]:
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
        

    @abstractmethod
    def find(self, search_string : str = None, limit : str = None) -> List[str]:
        """Finds genotype tags that match the search string. 

        Parameters
        ----------
        search_string : str
            The search string to look for in the genotype tags. 

        Returns
        -------
        List[str]
            A list of matching genotype tags. 
        """
    
    @abstractmethod
    def insert(self, data : InsertGeneticApplicationModel, user_tag : str) -> bool:
        """Inserts a new genotype into the database.
        This method should be used to insert a genotype. The components will be created from here.
        Parameters
        ----------
        data : InsertGeneticApplicationModel
            The genotype information to be inserted.
        user_tag : str
            The user who is inserting the genotype.
        Returns
        -------
        bool
            True if the insertion was successful, False otherwise.
        """

        return True

    @abstractmethod
    def insert_genotype(self, tag : str,  text : str, component_tags : List[str], user_tag : str, description : str|None, publication : str|None, technical_text : str|None, ) -> bool:
        """Inserts a new genotype into the database.
        Parameters
        ----------
        tag : str
            _description_
        text : str
            _description_
        component_tags : List[str]
            The tags the genotype is connected to. 
        description : str|None
            _description_
        publication : Optional[str], optional
            _description_, by default None
        technical_text : Optional[str], optional
            _description_, by default None
        """
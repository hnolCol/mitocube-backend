from abc import abstractmethod, ABC
from typing import List 
from neo4j import Driver

from config.models.genotype import MinimalGenotypeModel, GenotypeModel , InsertGeneticApplicationModel
from config.models.attributes import AttributeTree
from config.models.user import UserModel
from config.models.permissions import PermissionResponseModel 
from config.models.conditions_applications import ConditionApplicationTreeModel


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
    def count(self) -> int:
        "Counts the number of genotypes in the database."

    @abstractmethod
    def exists(self, tag : str) -> bool:
        "Checks if tag is associateed with genotype"
        
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
    def get_text(self, tag : str) -> str:
        "Gets the text of the genotype"

    @abstractmethod
    def get_description(self, tag : str) -> str:
        "Gets the description of the genotype"

    @abstractmethod
    def get_item(self, tag : str) -> dict[str]:
        "Gets the items of the genotype"

    @abstractmethod
    def get_proteins(self, tag : str) -> List[str]:
        "Gets the proteins affetced by the genotype"

    @abstractmethod
    def get_proteome(self, tag : str) -> str:
        "Gets the proteome affected by the genotype"

        
    @abstractmethod
    def find(self, search_string : str = None, user_tag : str = None, limit : str = None) -> List[str]:
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
    def insert(self, data : InsertGeneticApplicationModel, user_tag : str, tag : str = None) -> bool:
        """Inserts a new genotype into the database.
        This method should be used to insert a genotype. The components will be created from here.
        Parameters
        ----------
        data : InsertGeneticApplicationModel
            The genotype information to be inserted.
        user_tag : str
            The user who is inserting the genotype.
        tag : str, optional
            The tag of the genotype. If None, a new tag will be generated based on the components, by default None
            Should only be used when migrating data.
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

    @abstractmethod
    def edit(self, data : InsertGeneticApplicationModel, user_tag : str) -> bool:
        """Edits the genotype in the database.
        """

    @abstractmethod
    def edit_genotype(self, tag : str,  text : str, component_tags : List[str], user_tag : str, description : str|None, publication : str|None, technical_text : str|None, ) -> bool:
        """Edits the genotype in the database.
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


    @abstractmethod
    def count_samples(self, tag : str) -> int:
        "Counts the number of relationships of the genotype"

    @abstractmethod
    def delete(self, tag : str) -> bool:
        "Deletes a genotype by its tag. If is_active is True, the genotype will be marked as inactive instead of being deleted from the database."


    @abstractmethod
    def condition_applications(self, tag : str) -> List[str]:
        """Gets the condition applications associated with the genotype.

        Parameters
        ----------
        tag : str
            The genotype tag.

        Returns
        -------
        List[str]
            A list of condition application tags associated with the genotype.
        """

    @abstractmethod
    def condition_application_data(self, tag : str) -> List[ConditionApplicationTreeModel]:
        """Gets the condition application data associated with the genotype.

        Parameters
        ----------
        tag : str
            The genotype tag.

        Returns
        -------
        List[ConditionApplicationTreeModel]
            A list of condition application data associated with the genotype.
        """


    @abstractmethod
    def get_creator(self, tag: str) -> str | None:
        """Gets the creator of the genotype.

        Parameters
        ----------
        tag : str
            The genotype tag.

        Returns
        -------
        str | None
            The user tag of the creator of the genotype, or None if not found.
        """


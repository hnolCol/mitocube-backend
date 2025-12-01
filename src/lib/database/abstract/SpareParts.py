from __future__ import annotations
from abc import abstractmethod, ABC
from typing import List
from config.models.spareparts import SparepartInsertModel, SparepartResponseModel, SparepartBaseModel
from config.models.permissions import PermissionResponseModel

class SparePartsABC(ABC):
    """
    Abstract methods for Spare Parts database.

    Parameters
    ----------
    ABC : _type_
        The abstract class 
    """


    @abstractmethod
    def exists(self, tag: str) -> bool:
        """
        Check if a spare part with the given tag exists.

         Parameters
        ----------
        tag : str
            The spare part tag.

        Returns
        -------
        bool
            True if the spare part exists, otherwise False.
        """

    @abstractmethod
    def find(self, search_string: str = "", limit: int = 20) -> List[str]:
        """Find spare part by a search string and returns the tags that match. 

        Parameters
        ----------
        search_string : str, optional
            The query string, by default ""
        limit : int, optional
            The maximum number of spare parts to be returned., by default 20

        Returns
        -------
        List[str]
            The spare part tags. 
        """
    
    def get(self, tag: str) -> SparepartResponseModel:
        """
        Get the complete spare part model.

        Parameters
        ----------
        tag : str
            The spare part tag.

        Returns
        -------
        SparepartResponseModel
            A model containing all spare part data.
        """

        
    @abstractmethod
    def get_text(self, tag: str) -> str:
        """
        Gets the spare part text by its tag. 

        Parameters
        ----------
        tag : str
            The spare part tag.

        Returns
        -------
        str
            The text of the spare part.
        """

    @abstractmethod
    def get_description(self, tag: str) -> str:
        """
        Get the description of the spare part by its tag. 

        Parameters
        ----------
        tag : str
            The spare part tag.

        Returns
        -------
        str
            The description of the spare part.
        """

    @abstractmethod
    def get_company(self, tag: str) -> str:
        """
        Get the name of the company of the spare part by its tag.

        Parameters
        ----------
        tag : str
            The spare part tag.

        Returns
        -------
        str
            The company of the spare part.
        """

    @abstractmethod
    def get_product_id(self, tag: str) -> str:
        """
        Get the product ID of the spare part by its tag.

        Parameters
        ----------
        tag : str
            The spare part tag.

        Returns
        -------
        str
            The product ID.
        """

    @abstractmethod
    def get_price(self, tag: str) -> float | int:
        """
        Get the price of the spare part by its tag.

        Parameters
        ----------
        tag : str
            The spare part tag.

        Returns
        -------
        float | int
            The price of the spare part.
        """

    @abstractmethod
    def get_link(self, tag: str) -> str:
        """
        Get the URL for the spare part.

        Parameters
        ----------
        tag : str
            The spare part tag.

        Returns
        -------
        str
            A URL string pointing to a product page or resource.
        """


    @abstractmethod
    def insert(self, sparepart: SparepartInsertModel, user_tag: str = None) -> bool:
        """
        Insert a new spare part into the database.

        Parameters
        ----------
        sparepart : SparepartInsertModel
            The model containing all required fields for creating a spare part.

        Returns
        -------
        bool
            True if the insertion was successful, otherwise False.
        """


    @abstractmethod
    def update(self, tag: str, sparepart: SparepartBaseModel, user_tag: str = None) -> bool:
        """
        Update an existing spare part in the database.

        Parameters
        ----------
        tag : str
            The spare part tag to be updated.
        sparepart : SparepartModel
            Model containing updated field values.

        Returns
        -------
        bool
            True if the update was successful.
        """


    @abstractmethod
    def delete(self, tag: str) -> bool:
        """
        Delete a spare part from the database.

        Parameters
        ----------
        tag : str
            The spare part tag.

        Returns
        -------
        bool
            True if the deletion was successful, otherwise False.
        """



    
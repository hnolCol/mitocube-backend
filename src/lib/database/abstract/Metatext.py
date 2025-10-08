from __future__ import annotations

from abc import abstractmethod, ABC
# from datetime import timedelta
from typing import List, Dict, Optional, Tuple, Literal  # , Any
from deprecated import deprecated
import pandas as pd


class MetaTextABC(ABC):
    """Abstract class to handle metatexts.
    Metatexts are displayed to all users and generally public.
    Metatexts are posted if a new dataset is available.
    """
    
    @abstractmethod
    def exists(self, tag : str) -> bool:
        """Checks if a given tag is associates with a metatext

        Parameters
        ----------
        tag : str
            The metatext tag

        Returns
        -------
        bool
            If the tag is associated with a metatext
        """
    
    
    @abstractmethod
    def insert(self, title : str, text : str, submission_tag : str, user_tag : str) -> bool:
        """Adds a metatext to the metatext pool.

        Parameters
        ----------
        title : str
            The title of the metatext
        text : str
            The actual metatext
        submission_tag : str
            The submission tag the metatext is associated with
        user_tag : str
            The user tag of the user creating the metatext

        Returns
        -------
        bool
            If the metatext was successfully added to the pool

        Exceptions
        ----------
        
        """

    @abstractmethod
    def get(self, tag : str) -> str:
        """Returns the metatext by its tag.

        Parameters
        ----------
        tag : str
            The metatext tag

        Returns
        -------
        str
            The metatext associated with the given tag

        Exceptions
        ----------
        Raises a KeyError if the tag is not found.
        """
        
    @abstractmethod
    def update(self, tag : str, user_tag : str, title : str = None, text : str = None) -> bool:
        """Updates a metatext by its tag.

        Parameters
        ----------
        tag : str
            The metatext tag
        user_tag : str
            The user tag of the user updating the metatext
        title : str, optional
            The new title of the metatext, by default None
        text : str, optional
            The new metatext, by default None

        Returns
        -------
        bool
            If the metatext was successfully updated

        Exceptions
        ----------
        Raises a KeyError if the tag is not found.
        """
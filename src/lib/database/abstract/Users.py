from __future__ import annotations

from abc import abstractmethod, ABC
from collections import OrderedDict
# from datetime import timedelta
from typing import List, Dict, Optional, Tuple, Literal  # , Any
from deprecated import deprecated

from config.models.user import UserModel, UserModelForRegistration


class UserABC(ABC):
    
    @abstractmethod
    def check(self) -> None:
        "Check if users exists, if not create the lead account."
    
    
    @abstractmethod
    def get_tags(self, limit : int) -> List[str]:
        ""
    
    @abstractmethod 
    def add_user(self, user_props : UserModelForRegistration):
        ""

    @abstractmethod
    def add_users(self, users : List[UserModel]):
        """Adds users to the database from a list of users

        Parameters
        ----------
        users : List[UserModel]
            The users to be added using the common pydantic UserModel. 
        """
        
    @abstractmethod
    def block_user_by_tag(self, tag : str) -> bool:
        ""
    
    @abstractmethod
    def count(self) -> int:
        """The number of users in the database.
        Blocked users are not counted. 
        
        Returns
        -------
        int
            The total number of users. 
        """
    
    def exists(self, tag : str) -> bool:
        return self.is_user(tag)
    
    
    @abstractmethod
    def find(self, search_string : str = None, limit : int = 40) -> List[str]:
        """Finds user by 'search_string' string. The result is limited to a number of
        users given by 'limit'.

        Parameters
        ----------
        search_string : str
            The query string used to filter the data. If the query is None, all users are returned respecting the limit.
        limit : int, optional
            The maximum of users that should be returned, by default 40

        Returns
        -------
        List[str]
            List of users tags. The maximum length
            is limit (default 40) but can be smaller if less user match.
        """
    
    @abstractmethod
    def get_user_by_email(self, email : str) -> None|UserModel:
        """Returns the user in the database using the database. 

        Parameters
        ----------
        email : str
            The email that is associated with an user.

        Returns
        -------
        None|UserModel
            None if not found otherwise the user. 
        """

    @abstractmethod
    def get_user_by_tag(self, tag : str) -> None|UserModel:
        ""
        
    @abstractmethod
    def get_users_by_tags(self, tags : List[str] = None) -> List[UserModel]:
        """Get all users from the database that match the given tags.
    
        Parameters
        ----------
        tags : List[str]
            The tags associated with users. If the tag is not present in the database
            it is simply ignored. If None, it returns all users in the database, default None

        Returns
        -------
        List[UserModel]
            Users that are associated with the given tags.
            

        Raises
        ------
        Exception
            If the database query resulted in an error. 
        """
        
    @abstractmethod
    def get_user_submission_views(self, tag : str, limit : int = None) -> List[str]:
        "Returns the submissions that have been viewed by the user."
            
    @abstractmethod
    def delete_user(self, tag : str) -> bool:
        "" 
    
    
    @abstractmethod 
    def is_user(self, tag : str) -> bool:
        """Checks if a user is associated with the 
        given tag. Use this method to check if a user
        exists. The function ```exists``` is an alias. 

        Parameters
        ----------
        tag : str
            The user tag to test.

        Returns
        -------
        bool
            If the user with the given tag is present.

        Raises
        ------
        Exception
            If the database query resulted in an error. 
        """
    @abstractmethod
    def is_user_active(self, tag: str) -> bool:
        """Checks if a user is active by its tag.

        Parameters
        ----------
        tag : str
            The tag of the user to be checked.

        Returns
        -------
        bool
            If the user is active.
        """


    @abstractmethod
    def update(self, tag : str, user_props : Dict) -> bool:
        """Updates props of the users. 
        All params in the user_props will be updated.
        The tag is not updatable. 

        Parameters
        ----------
        tag : str
            The user tag 
        user_props : Dict
            The props to be updated. 

        Returns
        -------
        bool
            If the update was successful
            
            
        Exception
        ---------
        ValueError
            If the updated email exists already. 
        """
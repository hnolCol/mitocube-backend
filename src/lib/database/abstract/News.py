from __future__ import annotations

from abc import abstractmethod, ABC
# from datetime import timedelta
from typing import List, Dict, Optional, Tuple, Literal  # , Any
from deprecated import deprecated
import pandas as pd
from config.models.news.news import NewsModel

class NewsABC(ABC):
    """Abstract class to handle news.
    News are displayed to all users and generally public. 
    News are posted if a new dataset is available. 
    """
    
    @abstractmethod
    def exists(self, tag : str) -> bool:
        """Checks if a given tag is associates with a news 

        Parameters
        ----------
        tag : str
            The news tag 

        Returns
        -------
        bool
            If the tag is associated with a news 
        """
    
    @abstractmethod
    def get(self, tags : List[str] = None, limit : int = 10) -> List[NewsModel]:
        """Returns the news either by tag or just the latest news. 

        Parameters
        ----------
        tags : List[str], optional
            if given, it will return the specific news by its tag, by default None
        limit : int, optional
            the maximum number of news to be returned, by default 10

        Returns
        -------
        List[News]
            The news to be returned. The length might be < limit, if not n > limit 
            news exist. IF tag is given, the length is always 1, since if the tag is not found
            an exception is thrown. 
            
        Exceptions
        ----------
        
        """
        
    @abstractmethod
    def insert(self, news : NewsModel) -> bool:
        """Adds a news to the news pool. 

        Parameters
        ----------
        news : News
            _description_

        Returns
        -------
        bool
            _description_
        """
        
    @abstractmethod
    def delete(self, tag : str) -> bool:
        """Deletes a specific news by its tag. 

        Parameters
        ----------
        label : str
            _description_

        Returns
        -------
        bool
            If the deletion was successful. 
        """
        
    @abstractmethod
    def update(self, news : NewsModel) -> bool:
        """Updates a news content. 

        Parameters
        ----------
        news : News
            _description_

        Returns
        -------
        bool
            _description_
        """
        
    
    

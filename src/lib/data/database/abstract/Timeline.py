from __future__ import annotations

from abc import abstractmethod, ABC
# from datetime import timedelta
from typing import List, Dict, Optional, Tuple, Literal  # , Any
from deprecated import deprecated
import pandas as pd
from config.models.news.news import NewsModel
from config.models.timeline import TimelineModel
class TimelineABC(ABC):
    """Abstract class to handle timeline.
    """
        
    @abstractmethod
    def delete(self, tag : str) -> bool:
        """Delete the timelin event by its tag. 

        Parameters
        ----------
        tag : str
            _description_

        Returns
        -------
        bool
            _description_
        """
        
        
    @abstractmethod
    def exists(self, tag : str) -> bool:
        """Checks if a given tag is associates with a news 

        Parameters
        ----------
        tag : str
            The timeline tag 

        Returns
        -------
        bool
            If the tag is associated with a news 
        """

    @abstractmethod
    def get(self, tag : str = None) -> List[TimelineModel]:
        ""

    @abstractmethod 
    def get_timeline_by_submission_tag(self, submission_tag : str):
        """Returns all timeline events for a 
        submission tag ordered the time of
        creation. 

        Parameters
        ----------
        tag : str
            _description_
        """
        
        
    @abstractmethod
    def insert(self):
        """Inserts a new timeline to the database
        """
    


        
    @abstractmethod
    def update(self, tag : str):
        """Updates a timeline event. 

        Parameters
        ----------
        tag : str
            _description_
        """
from __future__ import annotations

from abc import abstractmethod, ABC
from collections import OrderedDict
# from datetime import timedelta
from typing import List, Dict, Optional, Tuple, Literal  # , Any
from deprecated import deprecated

import pandas as pd

from config.settings.db import get_db_settings
from config.models.submissions.submissions import DatasetSubmissionModel
from config.models.submissions.comments import SubmissionCommentModel
from config.enums.states import SubmissionStatesEnums


class SubmissionSummaryABC(ABC):
    
    @abstractmethod
    def get(self, tag : str) -> List[str]:
        """Creates a summary as a string. 
        This is helpful to extract all required information and 
        put them in an Excel sheet. 

        Parameters
        ----------
        tag : str
            The submission tag

        Returns
        -------
        List[str]
            _Submission summary strings. 
        """

class SubmissionsABC(ABC):
    """Handles Submissions in the backend. 
    Notably, filtering submissions have an extra abstract class (see below)
    
    """
    
    @abstractmethod
    def count(self, state : SubmissionStatesEnums = None) -> int:
        """Counts the total number of submissions in the database

        Parameters
        ----------
        state : SubmissionStatesEnums, optional
            Submission state. If provided, the number of submissions in the 
            given state is returned, by default None

        Returns
        -------
        int
            The number of submission. 
        """
        
    
    def contains(self, tag : str) -> bool:
        "Alias for exists()."
        self.exists(tag)
    
    @abstractmethod
    def exists(self, tag : str) -> bool:
        """Checks if the given tag is associated with a 
        submission in the database. 

        Parameters
        ----------
        tag : str
            _description_

        Returns
        -------
        bool
            If the submission tag was found. 
        """
    
    @abstractmethod
    def get_title(self, tag : str) -> str:
        "Return the title of a given submission."
    
    @abstractmethod
    def get(self, tag : str) -> DatasetSubmissionModel:
        """Returns the submission

        Parameters
        ----------
        tag : str
            The associated tag. 

        Returns
        -------
        DatasetSubmissionModel
            _description_
            
        Exception
        ---------
        ValueError 
            If the tag does not exists 
        """
        
    @abstractmethod
    def get_comments(self, tag : str) -> list:
        "Returns the comments associated with a submission."
        
    @abstractmethod
    def get_samples(self, tag : str)-> List:
        "Returns the samples of a submission"
    
    @abstractmethod
    def get_state(self, tag: str) -> SubmissionStatesEnums:
        """Returns the current state of the submission 
        given by its tag. 

        Parameters
        ----------
        tag : str
            submission tag.  

        Returns
        -------
        SubmissionStatesEnums
            The state of the submission.
        """
    
    @abstractmethod
    def insert(self, submission : DatasetSubmissionModel) -> bool:
        """Adds a new submission to the database. 

        Parameters
        ----------
        submission : DatasetSubmissionModel
            _description_

        Returns
        -------
        bool
            _description_
            
            
        Exception
        ---------
        ProteomeNotFoundError 
            If the proteome is not yet in the database. 
        
        """
    
    
    @abstractmethod
    def insert_comment(self, tag : str, comment : SubmissionCommentModel):
        "Inserts a comment for a submission." 
    
    @abstractmethod
    def delete(self, tag : str) -> bool:
        """_summary_

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
    def update_state(self, tag : str, new_state : SubmissionStatesEnums, user_tag : str) -> bool: #model for meta data.
        """Updates the state of a submission.

        Parameters
        ----------
        tag : str
            The submission tag 
        new_state : SubmissionStatesEnums
            The new state the submission is in.
        user_tag : str 
            The user that changed the state. 
        Returns
        -------
        bool
            _description_
        """
        

class SubmissionFilterABC(ABC):
    
    
    
    @abstractmethod
    def get_all_tags(self, limit : int = None) -> List[str]:
        """Returns all submission tags in the database. 
        A submission that has data is also called a 'dataset' but every 
        'dataset' is a submission. 

        Parameters
        ----------
        limit : int, optional
            The maximum number of submissions that are returned. If None, all tags are returned, by default None

        Returns
        -------
        List[str]
            The submission tags in the database. 

        Raises
        ------
        Exception
            _description_
        """
        
    @abstractmethod
    def get_counts(self, tags : List[str] = None, by : Literal["user","state","attribute","attribute_value"] = "state") -> pd.DataFrame:
        """Returns the number of submissions/dataset associated with a certain param tag. A common
        use case would be to ask the question how many and which dataset/submission tags are associated with 
        a certain user or state or attribute_value (for example: Hypoxia, LC-Instrument)

        Parameters
        ----------
        tags : List[str]
            List of tags to consider, if None all submission are considered, by default None
        by : Literal[&quot;user&quot;,&quot;state&quot;,&quot;attribute&quot;,&quot;attribute_value&quot;], optional
            group counts by specific param. For example, setting by = "user" will list all submissions by 
            all users, by default "state"

        Returns
        -------
        pd.DataFrame
            The submission counts as a data frame, contains the following columns:
            ```
                - 'tag' (str) : The associated tag (user.tag, state.tag, attribute.tag or attribute_value.tag)
                - 'count' (int) : The count of submissions associated with the tag. 
                - 'tags' (List[str]) : The list of submission tags associated with the given tag.
            ```
        Raises
        ------
        Exception
            If the database query throws an exception. 
        """
        
    
    @abstractmethod
    def get(self,
            state : List[int] = None, 
            trait_tags : List[str] = None, 
            attribute_tag : List[str]= None, 
            user_tag : List[str] = None, 
            protein_tag : List[str] = None, 
            genotype_tag : List[str] = None,
            limit : int = 10) -> List[str]:
        """Returns the submission tags that match the filtering. 
        The filtering is performed using the AND operator throughout. 

        Parameters
        ----------
        state : List[int], optional
            _description_, by default None
        trait_tags : List[str], optional
            _description_, by default None
        attribute_tag : List[str], optional
            _description_, by default None
        user_tag : List[str], optional
            _description_, by default None
        protein_tag : List[str], optional
            _description_, by default None
        genotype_tag : List[str], optional
            _description_, by default None
        limit : int, optional
            The maximum number of submissions to be returned that match the filtering, by default 10

        Returns
        -------
        List[str]
            The list of submission tags 

        Raises
        ------
        Exception
            _description_
        """

    
from __future__ import annotations

from abc import abstractmethod, ABC
from collections import OrderedDict
# from datetime import timedelta
from typing import List, Dict, Optional, Tuple, Literal  # , Any
from deprecated import deprecated

import pandas as pd

from config.settings.db import get_db_settings
from config.models.submissions.submissions import DatasetSubmissionModel, AttributeTree
from config.models.submissions.comments import SubmissionCommentModel
from config.models.submissions.quantifications import ProteinGroupQuantificationModel, PrecursorQuantificationModel
from config.models.conditions_applications import ConditionApplicationAttributeModel, ConditionApplicationTreeModel
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
    def get_research_aim(self, tag: str) -> str:
        "Returns the research aim of the submission by its tag."
    
    @abstractmethod
    def get_title(self, tag : str) -> str:
        "Return the title of a given submission."
        
    @abstractmethod
    def set_title(self, tag : str, title : str)-> bool:
        "Sets the title of the submission."
    
    @abstractmethod
    def get_conditions_applications(self, tag : str, group_by_attribute : bool = False) -> List[str]|List[ConditionApplicationAttributeModel]:
        """Returns the condition application tag for the submission by its tag.
        
        Parameters
        ----------
        tag : str
            The submission tag.
        group_by_attribute : bool, optional
            If True, the condition applications are grouped by attribute, by default False  
        Returns
        -------
        List[str]|List[Dict]
            The condition application tags for the submission.
            If group_by_attribute is True, a list of dictionaries is returned where each dictionary has the following structure:
            ```
            {
                "attribute_tag": str,
                "condition_application_tags": List[str]
            }
            ```
            If group_by_attribute is False, a list of condition application tags (str) is returned.
        """

    @abstractmethod
    def condition_application_data(self, tag : str) -> List[ConditionApplicationTreeModel]:
        """Gets the condition application data associated with the submission.

        Parameters
        ----------
        tag : str
            The submission tag.

        Returns
        -------
        List[ConditionApplicationTreeModel]
            A list of condition application data associated with the submission.
        """


        
    @abstractmethod
    def get_created_at(self, tag : str) -> float:
        """Returns the created at timestamp of a submission.
        
        Parameters
        ----------
        tag : str
            The submission tag.

        Returns
        -------
        float
            The created at timestamp of the submission.
        """
        
    @abstractmethod
    def get_durations_between_states(state_01 : SubmissionStatesEnums, state_02 : SubmissionStatesEnums) -> List[Dict]:
        """Returns the duration for each submission between two states. 
        For example, the average duration between SUBMITTED and DONE. 

        Parameters
        ----------
        state_01 : SubmissionStatesEnums
            The first state.
        state_02 : SubmissionStatesEnums
            The second state.

        Returns
        -------
        List[Dict]
            List of dictionaries with the following structure:
            ```
            {
                "submission_tag": str,
                "duration": float # duration in milliseconds
            }
            ```
        """
        pass

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
    def get_samples(self, tag : str)-> List[str]:
        "Returns the samples of a submission"
    
    @abstractmethod
    def get_states(self) -> List[int]:
        "Returns the available submission states in the database."
        
    @abstractmethod
    def get_creator(self, tag : str) -> str| None:
        """
        Returns the user tag of the creator of the submission.
        Parameters
        ----------
        tag : str 
            The tag of the submission.  
            
        Returns     
        ------- 
        str   the user tag of the creator of the submission.
        """
    @abstractmethod   
    def get_users(self, tag : str) -> List[str]: 
        """Returns the users that are associated with the submission.
        Parameters 
        ----------
        tag : str
            The tag of the submission.  
        Returns     
        -------     
        List[str]   A list of user tags that are associated with the submission.
        """
    
    
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
    def get_views(self, tag : str) -> int:
        "Returns the number of views for a submission."
        
        
    @abstractmethod
    def get_protein_group_quantification_count(self) -> pd.DataFrame:
        """Returns the number of protein group quantifications for each submission. 

        Returns
        -------
        pd.DataFrame
             A data frame with the following columns:
            ```
                - 'submission_tag' (str) : The submission tag
                - 'protein_group_quantification_count' (int) : The number of protein group quantifications for the submission
                - 'user_tag' (str) : The user tag of the creator of the submission
                - 'created_at' (float) : The created at timestamp of the submission
            ```
            A dictionary with submission tags as keys and the number of protein group quantifications as values.
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
    def insert_protein_quantifications(self, tag : str, quantifications : List[ProteinGroupQuantificationModel]) -> int:   
        """
        Inserts protein quantifications for a given submission.

        Parameters
        ----------
        tag : str
            The tag of the submission.
        quantifications : List[Dict]
            List of protein quantifications to insert.

        Returns
        -------
        int
            Number of inserted protein quantifications.
        """
    @abstractmethod
    def insert_precursor_quantifications(self, tag : str, quantifications : List[PrecursorQuantificationModel]) -> int:   
        """
        Inserts precursor quantifications for a given submission.

        Parameters
        ----------
        tag : str
            The tag of the submission.
        quantifications : List[Dict]
            List of precursor quantifications to insert.

        Returns
        -------
        int
            Number of inserted precursor quantifications.
        """
    @abstractmethod  
    def insert_research_aim(self, tag : str, research_aim : str, user_tag : str) -> bool:
        """Inserts a research aim for a given submission.

        Parameters
        ----------
        tag : str
            The submission tag
        research_aim : str
            The research aim to insert
        user_tag : str
            The user tag of the user inserting the research aim

        Returns
        -------
        bool
            True if the research aim was inserted successfully, False otherwise
        """        

    @abstractmethod
    def insert_view(self, tag : str, user_tag : str) -> bool:
        "Inserts a view for a submission."

    @abstractmethod
    def insert_comment(self, tag : str, comment : SubmissionCommentModel):
        "Inserts a comment for a submission." 
        
        
    @abstractmethod
    def insert_attributes(self, tag : str, traits : List[AttributeTree]) -> bool:
        """Inserts the dataset attributes for a submission. 
        The dataset attributes are the traits that are associated with the submission.
        """
        
    
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
    @abstractmethod
    def quantification_exists(self, tag : str, type : Literal["proteins","precursors","any"]) -> bool:
        """Checks if samples have quantification data for a given submission."""
        pass 

    @abstractmethod
    def get_proteins_in_submission(self, tag: str) -> List[str]:
        """
        Returns all protein tags that are quantified in a submission.
        
        Parameters
        ----------
        tag : str
            The submission tag
            
        Returns
        -------
        List[str]
            List of protein tags
        """


    @abstractmethod
    def edit_condition_applications(self, tag: str, attribute_trees: List[AttributeTree]) -> bool:

        """Edits a condition application that is connected to the submission.
        Replaces the existing CA relationship with a new one, without deleting the CA node itself.
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
    def group_by_state(self, tags : List[str] = None) -> Dict[str, List[str]]:
        """Groups the submission tags by state. 
        Parameters
        ----------
        tags : List[str], optional
            The submission tags to consider, if None all submission are considered, by default None

        Returns
        -------
        Dict[str, List[str]]
            A dictionary where the keys are the state tags and the values are the submission tags associated with the state. 
        """
    
    @abstractmethod
    def find(self,
            state : List[int] = None, 
            trait_tags : List[str] = None, 
            attribute_tag : List[str]= None, 
            user_tag : List[str] = None, 
            protein_tag : List[str] = None, 
            genotype_tag : List[str] = None,
            ordered : bool = True,
            search_string : str = None,
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
        ordered : bool, optional
            If True, the results are ordered by the submission creation date in descending order, by default True
        search_string : str, optional
            A string to search for in the submission tags. If provided, the filtering is done on the search string, by default None
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

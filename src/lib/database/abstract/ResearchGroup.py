from abc import abstractmethod, ABC 
from typing import List, Dict 

from config.models.researchgroup import ResearchGroupModel, ResearchGroupInput


class ResearchGroupABC(ABC):
    def __init__(self) -> None:
        ""
        
    @abstractmethod  
    def insert_users(self, tag : str, user_tags : List[str]):
        " "
    @abstractmethod
    def exists(self, tag : str) -> bool:
        """ Checks if a research group with the given tag exists in the database."""
    @abstractmethod
    def get(self, tag : str) -> ResearchGroupModel:
        ""
    @abstractmethod
    def count(self) -> int:
        "Returns the number of research groups in the database"
    @abstractmethod
    def get_users_count(self, tag : str) -> int:
        " "
    @abstractmethod
    def get_submission_tags(self, tags : str) -> List[str]:
        "Returns the submission tags associated with the research group"
        
    @abstractmethod
    def get_submissions_count(self, tag : str) -> int:
        ""
    @abstractmethod
    def get_samples_count(self, tag : str) -> int:
        "Returns the number of samples associated with the research group"
        
    @abstractmethod    
    def insert(self, research_group):
        """
        Inserts a new research group into the database.
        """
        
        
    @abstractmethod
    def delete(self, tag : str) -> bool:
        ""
        
        
    @abstractmethod
    def update(self, tag : str, research_group : ResearchGroupInput) -> bool:
        """Updates the properties of the research group with the given tag."""
        
    @abstractmethod
    def find(self, search_string: str = None, user_tags: List[str] = None, submission_tags: List[str] = None, limit: int = 20) -> List[str]:
        """Finds research group tags that match the search string, user tags, or submission tags."""
        
    @abstractmethod
    def get_heads(self, tag : str) -> List[str]:
        "Returns the user tags of the research group heads (PIs) of the given research group"

    @abstractmethod
    def is_head(self, user_tag : str, group_tag : str = None) -> bool:
        """Checks if the user is a head (PI) of the given research group (or of any group if no group tag is given)"""

    @abstractmethod
    def get_headed_group_tags(self, user_tag : str) -> List[str]:
        """Returns the tags of the research groups the user is a head (PI) of"""

    @abstractmethod
    def get_shared_submissions_overview(self, user_tag : str) -> List[Dict]:
        """Returns the sharing overview for the head (PI): per submission of the user and their
        headed groups, the owner, the shared consortiums (approved and pending) and the
        collaborating users"""

    @abstractmethod
    def get_explore_disabled(self, tag : str) -> bool:
        "Returns whether the head (PI) of the research group disabled the explore visibility of the groups submissions"

    @abstractmethod
    def set_explore_disabled(self, tag : str, disabled : bool) -> bool:
        "Sets whether the head (PI) of the research group disabled the explore visibility of the groups submissions. When disabling, all collaboration access (COLLABORATES) of the groups submissions is revoked"

    @abstractmethod
    def get_explore_disabled_group_tags(self) -> List[str]:
        "Returns the tags of all research groups whose head (PI) disabled the explore visibility"

    @abstractmethod
    def set_head(self, group_tag : str, user_tag : str):
        "Makes the user a head (PI) of the research group"

    @abstractmethod
    def remove_head(self, group_tag : str, user_tag : str):
        "Removes the user as head (PI) of the research group"

    @abstractmethod
    def set_subgroup(self, parent_tag : str, child_tag : str):
        "Defines a parent-child relationship between two research groups, where the child group is a subgroup of the parent group."

    @abstractmethod
    def get_sharing_overview(self) -> List[Dict]:
        """Returns the platform-wide sharing overview for admins and curators: one entry per
        submission shared in any way, with the submission and owner tags, the owners research
        groups, the approved and pending consortium shares, the collaborating users (explore
        view shares) and the pending collaboration requests"""
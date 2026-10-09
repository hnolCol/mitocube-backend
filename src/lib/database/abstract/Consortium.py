from abc import abstractmethod, ABC
from typing import List, Dict
from config.models.consortium import ConsortiumModel, ConsortiumInput


class ConsortiumABC(ABC):
    def __init__(self) -> None:
        """
        """

    @abstractmethod
    def insert(self, tag : str, consortium : ConsortiumInput) -> bool:
        """ """

    @abstractmethod
    def exists(self, tag : str) -> bool:
        """ """

    @abstractmethod
    def get(self, tag : str) -> ConsortiumModel:
        """ """

    @abstractmethod
    def delete(self, tag : str) -> bool:
        """ """

    @abstractmethod
    def find(self, search_string : str = None, group_tags : List[str] = None, limit : int = 40) -> List[str]:
        """Finds consortium tags that match the search string or contain the given research groups."""

    @abstractmethod
    def get_tags(self, limit : int = 40) -> List[str]:
        """Returns the tags of all consortiums, ordered by creation date"""

    @abstractmethod
    def get_groups(self, tag : str) -> List[str]:
        """Returns the research group tags that are members of the consortium"""

    @abstractmethod
    def insert_groups(self, tag : str, group_tags : List[str]):
        """Adds research groups to the consortium"""

    @abstractmethod
    def remove_groups(self, tag : str, group_tags : List[str]):
        """Removes research groups from the consortium"""

    @abstractmethod
    def get_submission_tags(self, tag : str) -> List[str]:
        """Returns the submission tags that are shared with the consortium"""

    @abstractmethod
    def share_submission(self, consortium_tag : str, submission_tag : str) -> bool:
        """Shares a submission with the consortium"""

    @abstractmethod
    def unshare_submission(self, consortium_tag : str, submission_tag : str) -> bool:
        """Removes a submission from the consortium"""

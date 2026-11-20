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
    def count(self) -> int:
        "Returns the number of consortiums"
    @abstractmethod
    def delete(self, tag : str) -> bool:
        """ """

    @abstractmethod
    def find(self, search_string : str = None, group_tags : List[str] = None, user_tags : List[str] = None, limit : int = 40) -> List[str]:
        """Finds consortium tags that match the search string, contain the given research groups or that the given users research groups belong to."""

    @abstractmethod
    def get_tags(self, limit : int = 40) -> List[str]:
        """Returns the tags of all consortiums, ordered by creation date"""

    @abstractmethod
    def get_groups(self, tag : str) -> List[str]:
        """Returns the research group tags that are members of the consortium"""

    @abstractmethod
    def get_user_tags(self, tag : str) -> List[str]:
        """Returns the user tags of all users that are direct members of the consortium"""

    @abstractmethod
    def get_eligible_user_tags(self, tag : str) -> List[str]:
        """Returns the user tags of all users that are members of the consortiums eligible research groups"""

    @abstractmethod
    def find_by_user(self, user_tag : str, limit : int = 40) -> List[str]:
        """Returns the tags of all consortiums the user is a member of, either directly or
        as a member of one of the consortiums eligible research groups"""

    @abstractmethod
    def find_by_user_with_terms(self, user_tag : str, limit : int = 40) -> List[str]:
        """Returns the tags of all consortiums the user is a member of and whose terms were agreed by the users groups"""

    @abstractmethod
    def get_terms_group_tags(self, consortium_tag : str) -> List[str]:
        """Returns the tags of the eligible research groups that agreed to the consortium terms"""

    @abstractmethod
    def agree_terms(self, consortium_tag : str, group_tag : str, user_tag : str) -> bool:
        """Records the research groups agreement to the consortium terms"""

    @abstractmethod
    def revoke_terms(self, consortium_tag : str, group_tag : str) -> bool:
        """Revokes the research groups agreement to the consortium terms"""

    @abstractmethod
    def user_has_terms(self, consortium_tag : str, user_tag : str) -> bool:
        """Checks if one of the users research groups agreed to the consortium terms"""

    @abstractmethod
    def find_pending_terms_for_head(self, user_tag : str) -> List[Dict]:
        """Returns the consortiums where the user heads an eligible group without terms agreement"""

    @abstractmethod
    def find_consortiums_with_pending_terms_for_user(self, user_tag : str) -> List[str]:
        """Returns the consortiums the user is a member of where none of their groups agreed to the terms"""

    @abstractmethod
    def insert_groups(self, tag : str, group_tags : List[str], user_tag : str = None):
        """Adds research groups to the consortium as eligible groups and joins their heads (PIs) as members"""

    @abstractmethod
    def remove_groups(self, tag : str, group_tags : List[str]):
        """Removes research groups from the consortium, blocked while dependent members exist"""

    @abstractmethod
    def insert_users(self, tag : str, user_tags : List[str], user_tag : str = None):
        """Adds users as direct members of the consortium if they are eligible"""

    @abstractmethod
    def remove_users(self, tag : str, user_tags : List[str]):
        """Removes direct user memberships, blocked while dependent members exist"""

    @abstractmethod
    def is_head_of_user_in_consortium(self, head_tag : str, user_tag : str, consortium_tag : str) -> bool:
        """Checks if the user is a head (PI) of an eligible group of the consortium the given user is a member of"""

    @abstractmethod
    def insert_membership_request(self, consortium_tag : str, user_tag : str, kind : str, requested_by : str) -> bool:
        """Creates a pending membership request of kind 'add' or 'remove' for the user"""

    @abstractmethod
    def get_pending_membership_requests(self, consortium_tag : str = None) -> List[Dict]:
        """Returns all pending membership requests, optionally restricted to one consortium"""

    @abstractmethod
    def get_pending_membership_requests_for_head(self, user_tag : str) -> List[Dict]:
        """Returns the pending membership requests that concern the research groups the user leads"""

    @abstractmethod
    def approve_membership_request(self, consortium_tag : str, user_tag : str, decided_by : str) -> bool:
        """Approves a pending membership request"""

    @abstractmethod
    def deny_membership_request(self, consortium_tag : str, user_tag : str) -> bool:
        """Denies a pending membership request"""

    @abstractmethod
    def get_submission_tags(self, tag : str) -> List[str]:
        """Returns the submission tags that are shared with the consortium"""

    @abstractmethod
    def share_submission(self, consortium_tag : str, submission_tag : str, user_tag : str, approved : bool = False) -> bool:
        """Shares a submission with the consortium. If approved is False, the share request is
        created with status pending and requires the approval of a research group head (PI)."""

    @abstractmethod
    def get_pending_share_requests_for_head(self, user_tag : str) -> List[Dict]:
        """Returns the pending share requests that the given research group head (PI) can approve"""

    @abstractmethod
    def approve_share_request(self, consortium_tag : str, submission_tag : str, user_tag : str) -> bool:
        """Approves a pending share request, making the submission accessible to the consortium"""

    @abstractmethod
    def deny_share_request(self, consortium_tag : str, submission_tag : str) -> bool:
        """Denies a pending share request, removing the pending relation"""

    @abstractmethod
    def unshare_submission(self, consortium_tag : str, submission_tag : str) -> bool:
        """Removes a submission from the consortium"""

    @abstractmethod
    def is_head_of_submission_owner(self, user_tag : str, submission_tag : str) -> bool:
        """Checks if the user is a head (PI) of a research group the owner (creator) of the submission is a member of"""

    @abstractmethod
    def get_pending_consortium_tags(self, submission_tag : str) -> List[str]:
        """Returns the tags of consortiums with a pending share request for the submission"""
    
    @abstractmethod
    def find_joinable_consortiums_for_user(self, user_tag : str) -> List[str]:
        """Returns the consortiums whose terms were agreed by one of the users groups while the user is not a direct member yet"""


    @abstractmethod
    def get_pending_membership_requests_relevant_to(self, user_tag : str, group_tags : List[str]) -> List[Dict]:
        """Returns the pending membership requests that concern members of the given research
        groups (the groups a head (PI) leads or a group curator curates), plus the requests
        the given user filed themselves or that concern themselves"""

    @abstractmethod
    def get_group_sharing_overview(self) -> List[Dict]:
        """Returns the consortium sharing overview for admins and curators: one entry per consortium
        with the member research groups and whether each group agreed to the consortium terms"""
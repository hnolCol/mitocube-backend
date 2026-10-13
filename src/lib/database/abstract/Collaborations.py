from abc import abstractmethod, ABC
from typing import List, Optional

from config.models.collaborations import (
    CollaborationRequestInput,
    CollaborationRequestModel,
    SubmissionExploreModel,
)


class CollaborationsABC(ABC):
    """Handles collaboration requests for submissions."""

    @abstractmethod
    def create_collaboration_request(self, submission_tag : str, requested_by : str, input : CollaborationRequestInput) -> Optional[str]:
        """Creates a pending collaboration request for a submission. Returns the
        request tag or None if a pending request already exists for this
        user/group and submission combination."""

    @abstractmethod
    def get_collaboration_request(self, request_tag : str) -> Optional[CollaborationRequestModel]:
        """Returns the collaboration request by its tag or None if not found."""

    @abstractmethod
    def has_pending_collaboration_request(self, submission_tag : str, requested_by : str) -> bool:
        """Checks if a pending collaboration request exists for the given user and submission."""

    @abstractmethod
    def approve_collaboration_request(self, request_tag : str, approved_by : str) -> bool:
        """Approves a pending collaboration request. The requested user/group is
        added as collaborator(s) of the submission and the request status is
        set to approved. Returns False if no pending request was found."""

    @abstractmethod
    def deny_collaboration_request(self, request_tag : str) -> bool:
        """Denies a pending collaboration request, removing the request relation.
        Returns False if no pending request was found."""

    @abstractmethod
    def get_collaboration_requests_for_submission(self, submission_tag : str) -> List[CollaborationRequestModel]:
        """Returns all collaboration requests for a submission."""

    @abstractmethod
    def get_pending_collaboration_requests_for_head(self, user_tag : str) -> List[CollaborationRequestModel]:
        """Returns the pending collaboration requests that the given research
        group head (PI) can approve: requests of members of the groups they lead
        and requests for submissions created by members of their groups."""

    @abstractmethod
    def get_pending_collaboration_requests_for_user(self, user_tag : str) -> List[CollaborationRequestModel]:
        """Returns the pending collaboration requests created by the given user."""

    @abstractmethod
    def explore(self, search_string : str = None, limit : int = 40) -> List[SubmissionExploreModel]:
        """Returns minimal metadata (title, owner, research group, state) of
        all submissions that match the search string. This is a discovery
        endpoint and must never return sensitive submission data."""

    @abstractmethod
    def has_approved_collaboration_request(self, submission_tag : str, user_tag : str) -> bool:
        """Checks if a collaboration request from this user for this submission
        has been approved (i.e. the user is already a collaborator)."""

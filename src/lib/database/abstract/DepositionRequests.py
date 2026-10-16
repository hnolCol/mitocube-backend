from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Literal, Optional

from config.models.requests import DepositionRequestModel, DepositionRequestInsertModel


class DepositionRequestsABC(ABC):
    """Handles user requests that a submission's data should be deposited
    to an external database (e.g. PRIDE).

    A user creates a pending deposition request for a submission. The
    request is visible to curators/admins only. Once the data have been
    deposited, a curator completes the request with the accession
    identifier, a link and an optional login token. The requester is
    notified and the deposition information is part of the submission
    overview.
    """

    @abstractmethod
    def insert(self, request: DepositionRequestInsertModel, user_tag: str) -> str:
        """Stores a new pending deposition request. Returns the request tag.
        Raises ValueError if the submission does not exist or if a pending
        deposition request for the submission exists already, regardless
        of the requesting user."""

    @abstractmethod
    def exists(self, tag: str) -> bool:
        """Checks if a deposition request with the given tag exists."""

    @abstractmethod
    def get(self, tags: List[str] = None,
            status: Literal["pending", "deposited", "rejected"] = None,
            submission_tag: str = None,
            user_tag: str = None,
            limit: int = 50) -> List[DepositionRequestModel]:
        """Returns deposition requests, optionally filtered by tags, status,
        submission or requesting user, newest first."""

    @abstractmethod
    def get_pending(self, limit: int = 50) -> List[DepositionRequestModel]:
        """Returns the pending deposition requests, newest first."""

    @abstractmethod
    def get_for_submission(self, submission_tag: str, limit: int = 10) -> List[DepositionRequestModel]:
        """Returns the deposition requests of a submission, newest first."""

    @abstractmethod
    def delete(self, tag: str) -> bool:
        """Deletes a pending deposition request. Returns True if a request was
        deleted. Raises ValueError if the request does not exist or is not
        pending."""

    @abstractmethod
    def complete(self, tag: str, reviewer_tag: str, identifier: str, url: str = None,
                 token: str = None, comment: str = None) -> DepositionRequestModel:
        """Marks a pending deposition request as deposited and stores the
        accession identifier, an optional url and an optional login token.
        Raises ValueError if the request does not exist or is not pending."""

    @abstractmethod
    def reject(self, tag: str, reviewer_tag: str, comment: str = None) -> DepositionRequestModel:
        """Rejects a pending deposition request. Raises ValueError if the
        request does not exist or is not pending."""

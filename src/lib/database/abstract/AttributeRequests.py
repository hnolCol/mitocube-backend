from __future__ import annotations
from abc import abstractmethod, ABC
from typing import List, Optional, Literal

from config.models.requests import AttributeRequestModel, AttributeRequestInsertModel


class AttributeRequestsABC(ABC):
    """Handles user requests to extend the controlled vocabulary.

    Users can request a new attribute (optionally with traits) or a new
    trait for an existing attribute. The proposal is stored as a pending
    request. Curators can accept the request (the attribute/trait is
    created and the request is marked accepted) or reject it (the request
    is marked rejected, no data are created).
    """

    @abstractmethod
    def insert(self, request: AttributeRequestInsertModel, user_tag: str) -> str:
        """Stores a new pending request. Returns the request tag.

        Parameters
        ----------
        request : AttributeRequestInsertModel
            The proposed attribute and/or trait.
        user_tag : str
            The tag of the requesting user.

        Returns
        -------
        str
            The tag of the created request.
        """

    @abstractmethod
    def exists(self, tag: str) -> bool:
        """Checks if a request with the given tag exists."""

    @abstractmethod
    def get(self, tags: List[str] = None, status: Literal["pending", "accepted", "rejected"] = None, limit: int = 50) -> List[AttributeRequestModel]:
        """Returns requests, optionally filtered by tags or status, newest first."""

    @abstractmethod
    def get_pending(self, limit: int = 50) -> List[AttributeRequestModel]:
        """Returns the pending requests, newest first."""

    @abstractmethod
    def accept(self, tag: str, reviewer_tag: str, comment: Optional[str] = None) -> AttributeRequestModel:
        """Accepts a pending request. The proposed attribute/trait is created
        and the request is marked accepted. Raises ValueError if the request
        does not exist or is not pending, or if the proposal collides with
        existing data."""

    @abstractmethod
    def reject(self, tag: str, reviewer_tag: str, comment: Optional[str] = None) -> AttributeRequestModel:
        """Rejects a pending request. The request is marked rejected and the
        proposal is not created. Raises ValueError if the request does not
        exist or is not pending."""

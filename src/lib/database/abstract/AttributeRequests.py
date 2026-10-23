from __future__ import annotations
from abc import abstractmethod, ABC
from typing import List, Optional, Literal

from config.models.requests import AttributeRequestModel, AttributeRequestInsertModel


class AttributeRequestsABC(ABC):
    """Handles user requests to extend the controlled vocabulary.

    Users can request a new attribute (optionally with traits) or a new
    trait for an existing attribute. The proposal is stored as a pending
    request. Curators can accept the request, optionally editing the
    proposal first (the attribute/trait is created and the request is
    marked accepted), or reject it (the request is marked rejected, no
    data are created).
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

        Raises
        ------
        ValueError
            If the target attribute does not exist (trait requests), the
            proposal exists already, or a pending request for it is open.
        """

    @abstractmethod
    def exists(self, tag: str) -> bool:
        """Checks if a request with the given tag exists."""

    @abstractmethod
    def get(self, tags: List[str] = None, status: Literal["pending", "accepted", "rejected"] = None,
            kind: Literal["attribute", "trait"] = None, user_tag: str = None, limit: int = 50) -> List[AttributeRequestModel]:
        """Returns requests matching all given filters, newest first.

        Parameters
        ----------
        tags : List[str], optional
            Restrict to these request tags.
        status : {"pending", "accepted", "rejected"}, optional
            Restrict to requests with this status.
        kind : {"attribute", "trait"}, optional
            Restrict to attribute or trait requests.
        user_tag : str, optional
            Restrict to requests created by this user.
        limit : int
            Maximum number of requests returned.

        Returns
        -------
        List[AttributeRequestModel]
        """

    @abstractmethod
    def get_pending(self, kind: Literal["attribute", "trait"] = None, limit: int = 50) -> List[AttributeRequestModel]:
        """Returns the pending requests, optionally filtered by kind, newest first."""

    @abstractmethod
    def accept(self, tag: str, reviewer_tag: str, comment: Optional[str] = None,
               edits: Optional[dict] = None) -> AttributeRequestModel:
        """Accepts a pending request. The proposed attribute/trait is created
        and the request is marked accepted.

        Parameters
        ----------
        tag : str
            The request tag.
        reviewer_tag : str
            The tag of the reviewing curator.
        comment : str, optional
            Review comment.
        edits : dict, optional
            Fields that override the stored proposal before it is created
            (e.g. priority, group_tags, text). The final proposal is
            written back to the request.

        Raises
        ------
        ValueError
            If the request does not exist or is not pending, or if the
            (edited) proposal collides with existing data.
        """

    @abstractmethod
    def reject(self, tag: str, reviewer_tag: str, comment: Optional[str] = None) -> AttributeRequestModel:
        """Rejects a pending request. The request is marked rejected and the
        proposal is not created. Raises ValueError if the request does not
        exist or is not pending."""
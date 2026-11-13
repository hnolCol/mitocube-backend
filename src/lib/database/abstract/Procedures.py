from __future__ import annotations
from abc import abstractmethod, ABC
from typing import List, Optional

from config.models.procedures import (
    ModularProcedureBaseModel,
    ModularProcedureSubmissionModel,
    PublishModularProcedureModel,
)



class ModularProceduresABC(ABC):
    """Abstract class to handle modular procedures.
    A modular procedure is a facility workflow module (similar to an SOP) that
    bundles a title, a description, condition applications and protocols.
    Submissions are assigned to modular procedures and travel through them in
    order; facility members (curators) mark a submission as done in a procedure
    so that it can proceed to the next one.
    Procedures are created and edited as drafts by curators. Once published,
    they receive a SHA-256 content hash and become immutable.
    """

    @abstractmethod
    def exists(self, tag: str) -> bool:
        "Checks if the given tag is associated with a modular procedure."

    @abstractmethod
    def insert(self, title: str, description: str, user_tag: str,
               condition_application_tags: List[str] = None,
               protocol_tags: List[str] = None) -> str:
        """Adds a new draft modular procedure.
        Returns the tag of the created procedure.
        Raises a ValueError if a procedure with the same tag already exists."""

    @abstractmethod
    def get(self, tag: str) -> ModularProcedureBaseModel:
        """Returns the modular procedure by its tag.
        Raises a KeyError if the tag is not found."""

    @abstractmethod
    def find(self, search_string: str = None, status: str = None, limit: int = None) -> List[str]:
        """Returns the tags of modular procedures, optionally filtered by a
        search string and status, sorted by creation date, most recent last."""

    @abstractmethod
    def update(self, tag: str, title: str, description: str, user_tag: str,
               condition_application_tags: List[str] = None,
               protocol_tags: List[str] = None) -> bool:
        """Updates a draft modular procedure.
        Raises a ValueError if the procedure does not exist or is published
        (published procedures are immutable)."""

    @abstractmethod
    def publish(self, tag: str, user_tag: str) -> PublishModularProcedureModel:
        """Publishes a draft modular procedure: computes the SHA-256 content
        hash, sets the status to PUBLISHED and locks the procedure.
        Raises a ValueError if the procedure does not exist or is already
        published."""

    @abstractmethod
    def link(self, tag: str, submission_tag: str, user_tag: str) -> bool:
        """Assigns a submission to the procedure. The link is appended at the
        end of the submission's procedure order.
        Raises a ValueError if the procedure does not exist or the submission
        is already linked."""

    @abstractmethod
    def unlink(self, tag: str, submission_tag: str) -> bool:
        """Removes the submission from the procedure.
        Raises a ValueError if the procedure does not exist or the link does
        not exist."""

    @abstractmethod
    def mark_done(self, tag: str, submission_tag: str, user_tag: str) -> bool:
        """Marks the submission as done in the given procedure.
        Raises a ValueError if the procedure does not exist or the submission
        is not linked."""

    @abstractmethod
    def reopen(self, tag: str, submission_tag: str) -> bool:
        """Reverts the done flag of the submission in the given procedure.
        Raises a ValueError if the procedure does not exist or the submission
        is not linked."""

    @abstractmethod
    def get_submissions(self, tag: str) -> List[ModularProcedureSubmissionModel]:
        """Returns the submissions linked to the given procedure with their
        link information (created_at, done, done_at, done_by).
        Raises a KeyError if the tag is not found."""

    @abstractmethod
    def get_submission_procedures(self, submission_tag: str) -> List[ModularProcedureSubmissionModel]:
        """Returns the procedures the given submission is linked to, ordered by
        the link position (the order in which the submission was assigned)."""

    @abstractmethod
    def get_condition_applications(self, tag: str) -> List[str]:
        """Returns the condition application tags of the given procedure.
        Raises a KeyError if the tag is not found."""

    @abstractmethod
    def get_protocols(self, tag: str) -> List[str]:
        """Returns the protocol tags of the given procedure.
        Raises a KeyError if the tag is not found."""

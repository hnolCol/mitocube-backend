from __future__ import annotations
from abc import abstractmethod, ABC
from typing import Dict, List, Optional

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
               condition_application_trees: List = None,
               protocol_tags: List[str] = None,
               plate_constraints: dict = None,
               input_attribute_tags: List[str] = None,
               output_attribute_tags: List[str] = None,
               success_submission_state: str = None,
               required_submission_state: str = None) -> str:
        """Adds a new draft modular procedure. Condition applications can be reused by
        tag or newly defined as hierarchical attribute/trait trees (like when inserting
        a submission); trees are resolved to condition application tags on insert.
        plate_constraints optionally fixes the required input/output plate format and
        type; input/output attribute tags declare the per-well attributes of the
        procedure; success_submission_state optionally names a submission state that
        is set automatically for the linked submissions on a successful execution;
        required_submission_state optionally restricts executions of the procedure to
        submissions in that state (None means unconstrained).
        Returns the tag of the created procedure.
        Raises a ValueError if a procedure with the same tag already exists."""

    @abstractmethod
    def get(self, tag: str) -> ModularProcedureBaseModel:
        """Returns the modular procedure by its tag.
        Raises a KeyError if the tag is not found."""

    @abstractmethod
    def find(self, search_string: str = None, status: str = None, limit: int = None, latest_only: bool = False) -> List[str]:
        """Returns the tags of modular procedures, optionally filtered by a
        search string and status, sorted by creation date, most recent last.
        If latest_only is True, only the highest-version procedure of each
        lineage is returned."""

    @abstractmethod
    def update(self, tag: str, title: str, description: str, user_tag: str,
               condition_application_tags: List[str] = None,
               condition_application_trees: List = None,
               protocol_tags: List[str] = None,
               plate_constraints: dict = None,
               input_attribute_tags: List[str] = None,
               output_attribute_tags: List[str] = None,
               success_submission_state: str = None,
               required_submission_state: str = None) -> bool:
        """Updates a draft modular procedure. Condition application trees are resolved
        to tags like on insert.
        Raises a ValueError if the procedure does not exist or is published
        (published procedures are immutable)."""

    @abstractmethod
    def publish(self, tag: str, user_tag: str) -> PublishModularProcedureModel:
        """Publishes a draft modular procedure: computes the SHA-256 content
        hash, sets the status to PUBLISHED and locks the procedure.
        Raises a ValueError if the procedure does not exist or is already
        published."""

    @abstractmethod
    def retire(self, tag: str, user_tag: str):
        """Retires a published modular procedure: the content and its SHA-256 hash are kept
        forever (procedures are never deleted, so their executions stay reproducible) but the
        procedure can no longer be assigned or executed — the UI shows it in a greyed out
        style. Existing links keep their module history and can still be completed.
        Raises a ValueError if the procedure does not exist, is a draft or is already retired."""

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

    @abstractmethod
    def execute(self, tag: str, execution, user_tag: str):
        """Starts a published modular procedure execution on a set of samples.
        Maps input plate wells to output plate wells (pooling and splitting
        supported). The execution is created in the RUNNING state; the linked
        submissions are only freed by finish_execution.
        Raises a ValueError if the procedure does not exist, is not published,
        a plate or sample does not exist, the plates do not match the plate
        layout constraints of the procedure or the transfer map is inconsistent."""

    @abstractmethod
    def get_occupied_output_wells(self, plate_tag: str):
        """Returns the positions of the plate's output wells blocked by executions (running or
        kept blocked) — the wells an execution setup must not map its outputs onto. Drafts and
        finished-unblocked executions do not block anything."""

    @abstractmethod
    def get_draft_executions_wells(self, plate_tag: str) -> Dict[str, List[str]]:
        """Returns a map of the plate's well positions to the tags of the DRAFT executions that
        use them (input or output side). Drafts block nothing — set ups use this map to warn
        about potential conflicts between parallel drafts (only the execution that starts
        first gets the wells)."""

    @abstractmethod
    def create_execution_draft(self, tag: str, user_tag: str):
        """Creates an empty DRAFT execution of a published modular procedure with a
        backend-generated ID. The design (plates, samples, transfer map, values)
        is saved via update_execution_draft and can be continued later; drafts do
        not block output wells until they are started via start_execution.
        Raises a ValueError if the procedure does not exist or is not published."""

    @abstractmethod
    def update_execution_draft(self, execution_tag: str, design_update, user_tag: str):
        """Saves the setup of a DRAFT execution, replacing the stored design wholesale.
        The design must be valid on its own (plates, samples and traits must exist,
        positions unique, transfer targets defined, declared sample numbers
        respected); the output well occupancy is only checked on start.
        Raises a KeyError if the execution does not exist and a ValueError if it is
        not a draft or the design is invalid."""

    @abstractmethod
    def start_execution(self, execution_tag: str, user_tag: str):
        """Starts a saved DRAFT as a run: the stored design is re-validated in full
        (including the output well occupancy) and the execution moves to RUNNING,
        blocking its output wells. Raises a KeyError if the execution does not exist
        and a ValueError if it is not a draft or the validation fails."""

    @abstractmethod
    def delete_execution_draft(self, execution_tag: str, user_tag: str):
        """Deletes a DRAFT execution (and only a draft): drafts are setup work, not
        recorded history. Raises a KeyError if the execution does not exist and a
        ValueError if it is not a draft."""

    @abstractmethod
    def finish_execution(self, execution_tag: str, outcome: str, user_tag: str, comment: str = None,
                         block_output_wells: bool = None):
        """Transitions a procedure execution to the given state (SUCCEEDED, FAILED
        or ABORTED); every state is recorded in the IN_STATE history (like
        submission states). Leaving RUNNING frees the submissions owning the
        placed samples (freed for the next module); a transition to SUCCEEDED
        applies the success effects (condition application adoption, optional
        success submission state). Finished executions can be corrected later
        (e.g. FAILED to SUCCEEDED); changing to the current state is rejected.
        Raises a KeyError if the execution does not exist and a ValueError if
        the outcome is invalid."""

    @abstractmethod
    def get_execution(self, execution_tag: str):
        """Returns the procedure execution by its tag.
        Raises a KeyError if the tag is not found."""

    @abstractmethod
    def get_executions(self, tag: str) -> List[str]:
        """Returns the tags of the executions of the given procedure, sorted by
        creation date, most recent last. Raises a KeyError if the procedure tag
        is not found."""

    @abstractmethod
    def create_version(self, tag: str, user_tag: str):
        """Creates a new draft version of the given published modular procedure,
        copying its content, condition applications and protocols. Submissions
        stay linked to the version they were assigned to.
        Raises a ValueError if the procedure does not exist or is not published."""

    @abstractmethod
    def get_versions(self, tag: str) -> List[str]:
        """Returns the tags of all versions in the lineage of the given procedure,
        oldest first. Raises a KeyError if the tag is not found."""

    @abstractmethod
    def get_execution_states(self, execution_tag: str) -> List:
        """Returns the state history of a procedure execution, newest state first.
        Raises a KeyError if the execution does not exist."""

    @abstractmethod
    def find_execution_tags(self, status: str = None, limit: int = None) -> List[str]:
        """Returns the tags of all procedure executions, newest first, optionally
        filtered by their current state."""

    @abstractmethod
    def find_execution_tags_by_submissions(self, submission_tags: List[str]) -> List[str]:
        """Returns the tags of the procedure executions that placed samples of the
        given submissions."""

    @abstractmethod
    def get_submission_sample_locations(self, submission_tag: str) -> List:
        """Returns the current plate locations of the samples of a submission: for
        every sample the wells of its most recent procedure execution (input and
        output side, with the plate tags). Samples that were never placed show no
        entry. Raises a KeyError if the submission does not exist."""

    @abstractmethod
    def get_sample_submission_map(self, sample_tags: List[str]) -> dict:
        """Returns a map of the given sample tags to the tags of the submissions
        owning them."""

    @abstractmethod
    def set_execution_metrics(self, execution_tag: str, well_metrics, user_tag: str):
        """Sets or updates the measured attribute values (metrics) of the output
        wells of a procedure execution. Raises a KeyError if the execution does
        not exist and a ValueError if a well is not an output well of the
        execution or an attribute does not exist."""

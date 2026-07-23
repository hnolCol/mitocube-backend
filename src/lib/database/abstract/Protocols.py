from __future__ import annotations
from config.models.protocols import InsertProtocolModel, UpdateProtocolModel, ProtocolBaseModel
from abc import abstractmethod, ABC
from typing import List


class ProtocolsABC(ABC):
    """Abstract class to handle protocols.
    Protocols describe the experimental or computational procedure used to
    generate a submission (e.g. sample preparation, acquisition, or analysis
    protocol) and are written in Markdown.
    Protocols are created independently and can then be linked to one or
    several submissions, allowing reuse of the same protocol across
    multiple submissions.
    """

    @abstractmethod
    def exists(self, tag: str) -> bool:
        """Checks if a given tag is associated with a protocol

        Parameters
        ----------
        tag : str
            The protocol tag

        Returns
        -------
        bool
            If the tag is associated with a protocol
        """

    @abstractmethod
    def insert(self, title: str, protocol_text: str, user_tag: str, doi : str = None, pubmed_id : str = None, url : str = None, ignore_exists_error: bool = False) -> bool:
        """Adds a protocol to the protocol pool.

        Parameters
        ----------
        title : str
            The title of the protocol
        protocol_text : str
            The actual protocol, formatted as Markdown
        user_tag : str
            The user tag of the user creating the protocol
        doi : str, optional
            The DOI of the protocol, by default None
        pubmed_id : str, optional
            The PubMed ID of the protocol, by default None
        url : str, optional
            The URL of the protocol, by default None
        ignore_exists_error : bool, optional
            If True, does not raise an error if the protocol already exists and returns False. If False, raises an error if the protocol already exists. By default False.

        Returns
        -------
        bool
            If the protocol was successfully added to the pool

        Exceptions
        ----------
        Raises a KeyError if the protocol already exists and ignore_exists_error is False.
        """

    @abstractmethod
    def get(self, tag: str) -> ProtocolBaseModel:
        """Returns the protocol by its tag.

        Parameters
        ----------
        tag : str
            The protocol tag

        Returns
        -------
        ProtocolBaseModel
            The protocol associated with the given tag

        Exceptions
        ----------
        Raises a KeyError if the tag is not found.
        """

    @abstractmethod
    def get_submissions(self, tag: str) -> List[str]:
        """Returns the submission tags linked to the given protocol tag.

        Parameters
        ----------
        tag : str
            The protocol tag

        Returns
        -------
        List[str]
            The submission tags linked to the protocol

        Exceptions
        ----------
        Raises a KeyError if the tag is not found.
        """

    @abstractmethod
    def find(self, search_string : str = None, submission_tags: List[str] = None, limit : int = None) -> List[str]:
        """Returns the tags of protocols. If submission_tag is provided, only
        protocols linked to the given submission are returned.
        The tags are sorted by creation date, most recent last.

        Parameters
        ----------
        search_string : str, optional
            A string to search for in protocol titles, by default None.
        submission_tags : List[str], optional
            The tags of the submissions to filter protocols, by default None (all protocols).

        Returns
        -------
        List[str]
            A list of protocol tags.
        """

    @abstractmethod
    def update(self, tag: str, user_tag: str, title: str = None, protocol_text: str = None) -> bool:
        """Updates a protocol by its tag.

        Parameters
        ----------
        tag : str
            The protocol tag
        user_tag : str
            The user tag of the user updating the protocol
        title : str, optional
            The new title of the protocol, by default None
        protocol_text : str, optional
            The new protocol text, formatted as Markdown, by default None

        Returns
        -------
        bool
            If the protocol was successfully updated

        Exceptions
        ----------
        Raises a KeyError if the tag is not found.
        """

    @abstractmethod
    def link(self, tag: str, submission_tag: str, user_tag : str, ignore_exists_error: bool = False) -> bool:
        """Links an existing protocol to a submission.

        Parameters
        ----------
        tag : str
            The protocol tag
        submission_tag : str
            The submission tag to link the protocol to
        user_tag : str
            The user tag of the user linking the protocol to the submission
        ignore_exists_error : bool, optional
            If True, does not raise an error if the link already exists and returns False. If False, raises an error if the link already exists. By default False.

        Returns
        -------
        bool
            If the protocol was successfully linked to the submission

        Exceptions
        ----------
        Raises a KeyError if the protocol tag is not found.
        Raises a KeyError if the link already exists and ignore_exists_error is False.
        """


    @abstractmethod
    def unlink(self, tag: str, submission_tag: str) -> bool:
        """Unlinks a protocol from a submission.

        Parameters
        ----------
        tag : str
            The protocol tag
        submission_tag : str
            The submission tag to unlink the protocol from

        Returns
        -------
        bool
            If the protocol was successfully unlinked from the submission

        Exceptions
        ----------
        Raises a KeyError if the protocol tag is not found.
        Raises a KeyError if the link does not exist.
        """

    @abstractmethod
    def delete(self, tag: str) -> bool:
        """Deletes the protocol identified by the given tag.

        Parameters
        ----------
        tag : str
            The protocol tag

        Returns
        -------
        bool
            If the protocol was successfully deleted

        Exceptions
        ----------
        Raises a KeyError if the tag is not found.
        """

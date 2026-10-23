from abc import abstractmethod, ABC
from typing import List, Optional

from config.models.messages import (
    ConversationInput,
    ConversationModel,
    ConversationResponseModel,
    MessageInput,
    MessageModel,
)


class MessagesABC(ABC):
    """Handles conversations and messages between users."""

    @abstractmethod
    def insert_conversation(self, created_by : str, conversation : ConversationInput) -> Optional[str]:
        """Creates a conversation with the given participants, optionally linked
        to a submission. Returns the conversation tag or None if it could not
        be created (e.g. a participant does not exist)."""

    @abstractmethod
    def exists(self, conversation_tag : str) -> bool:
        """Checks if a conversation with the given tag exists."""

    @abstractmethod
    def get_conversation(self, conversation_tag : str) -> Optional[ConversationModel]:
        """Returns the conversation by its tag or None if not found."""

    @abstractmethod
    def get_conversations_for_user(self, user_tag : str, submission_tag : str = None) -> List[ConversationResponseModel]:
        """Returns all conversations of the given user, optionally filtered by
        the linked submission."""

    @abstractmethod
    def get_conversations_for_submission(self, submission_tag : str) -> List[ConversationModel]:
        """Returns all conversations linked to the given submission."""

    @abstractmethod
    def is_participant(self, conversation_tag : str, user_tag : str) -> bool:
        """Checks if the user is a participant of the conversation."""

    @abstractmethod
    def add_participants(self, conversation_tag : str, user_tags : List[str]) -> bool:
        """Adds users as participants to an existing conversation. Users that are
        already participants are ignored. Returns False if the conversation does
        not exist or a user does not exist."""

    @abstractmethod
    def insert_message(self, conversation_tag : str, sender_tag : str, message : MessageInput) -> Optional[str]:
        """Adds a message to a conversation. Returns the message tag or None
        if the conversation does not exist."""

    @abstractmethod
    def get_messages(self, conversation_tag : str, limit : int = None) -> List[MessageModel]:
        """Returns all messages of a conversation ordered by creation date."""

    @abstractmethod
    def mark_read(self, conversation_tag : str, user_tag : str) -> bool:
        """Marks all messages of the conversation as read for the given user."""

    @abstractmethod
    def get_unread_count(self, conversation_tag : str, user_tag : str) -> int:
        """Returns the number of messages of the conversation that the user has
        not read yet (messages sent by other users)."""

    @abstractmethod
    def insert_system_message(self, user_tags : List[str], title : str, content : str,
                              sender_tag : str, submission_tag : Optional[str] = None) -> Optional[str]:
        """Creates a read-only conversation for the given users with a single
        system message (e.g. from MitoCube Support). The sender is not a user
        and is not a participant; recipients cannot reply.

        Returns
        -------
        Optional[str]
            The conversation tag, or None if a recipient does not exist.
        """

    @abstractmethod
    def is_read_only(self, conversation_tag : str) -> bool:
        """Returns True if the conversation is a read-only system notification."""
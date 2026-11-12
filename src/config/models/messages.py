from pydantic import BaseModel, Field, model_validator
from typing import List, Optional

from services.date import get_time_stamp


class MessageAttachmentModel(BaseModel):
    """An image attached to a message (support ticket conversations only)."""
    tag : str
    filename : str
    content_type : str
    size : int


class MessageModel(BaseModel):
    """A single message in a conversation."""
    tag : str = Field(..., description="Unique tag of the message.")
    created_at : float = Field(..., default_factory=get_time_stamp)
    sender_tag : str
    content : str
    read_by : List[str] = []
    attachments : List[MessageAttachmentModel] = []


class ConversationModel(BaseModel):
    """A conversation between two or more users, optionally linked to a submission.
    System notifications (e.g. from MitoCube Support) are read-only conversations
    with a single participant."""
    tag : str = Field(..., description="Unique tag of the conversation.")
    created_at : float = Field(..., default_factory=get_time_stamp)
    created_by : str
    user_tags : List[str] = []
    submission_tag : Optional[str] = None
    title : Optional[str] = None
    read_only : bool = False
    ticket_tag : Optional[str] = None   # set when the conversation belongs to a support ticket


class MessageInput(BaseModel):
    """Input model to post a message to a conversation. Text, attachments or both."""
    content : str = ""
    attachment_tags : List[str] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def _not_empty(self):
        if not self.content.strip() and not self.attachment_tags:
            raise ValueError("A message needs text or an attachment.")
        return self


class ConversationInput(BaseModel):
    """Input model to create a conversation."""
    user_tags : List[str] = Field(..., min_length=1)
    submission_tag : Optional[str] = None
    title : Optional[str] = None
    initial_message : Optional[str] = None


class ConversationResponseModel(ConversationModel):
    """Conversation with additional metadata for list views."""
    last_message_at : Optional[float] = None
    n_messages : Optional[int] = None
    unread : Optional[bool] = None
    last_message : Optional[str] = None
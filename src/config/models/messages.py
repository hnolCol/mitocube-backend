from pydantic import BaseModel, Field
from typing import List, Optional

from services.date import get_time_stamp


class MessageModel(BaseModel):
    """A single message in a conversation."""
    tag : str = Field(..., description="Unique tag of the message.")
    created_at : float = Field(..., default_factory=get_time_stamp)
    sender_tag : str
    content : str
    read_by : List[str] = []


class ConversationModel(BaseModel):
    """A conversation between two or more users, optionally linked to a submission."""
    tag : str = Field(..., description="Unique tag of the conversation.")
    created_at : float = Field(..., default_factory=get_time_stamp)
    created_by : str
    user_tags : List[str] = []
    submission_tag : Optional[str] = None
    title : Optional[str] = None


class MessageInput(BaseModel):
    """Input model to post a message to a conversation."""
    content : str = Field(..., min_length=1)


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

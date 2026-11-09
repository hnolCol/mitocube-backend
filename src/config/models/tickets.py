from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class TicketStatusEnum(str, Enum):
    OPEN = "Open"
    IN_PROGRESS = "In Progress"
    RESOLVED = "Resolved"


class TicketInput(BaseModel):
    title : str = Field(..., min_length = 3, max_length = 200)
    description : str = Field(..., min_length = 10, max_length = 10_000)


class TicketReplyInput(BaseModel):
    content : str = Field("", max_length = 10_000)
    resolve : bool = False   # True = mark as Resolved; otherwise a reply moves it to In Progress


class TicketCreatedResponse(BaseModel):
    tag : str
    reference : str


class TicketAttachmentModel(BaseModel):
    tag : str
    ticket_tag : str
    filename : str           # original filename as uploaded
    content_type : str       # detected MIME type, e.g. image/png
    size : int               # size in bytes
    extension : str          # stored file extension, e.g. .png
    uploaded_by : str
    uploaded_by_name : Optional[str] = None
    created_at : int


class TicketModel(BaseModel):
    tag : str
    reference : str
    title : str
    description : str
    status : TicketStatusEnum
    created_at : int
    updated_at : int
    raised_by : str
    raised_by_name : Optional[str] = None
    assigned_to : Optional[str] = None
    assigned_to_name : Optional[str] = None
    conversation_tag : Optional[str] = None
    last_message_at : Optional[int] = None
    awaiting_reply : bool = False   # no reply yet, or user wrote last
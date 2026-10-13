from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException

from lib.database.Database import get_db
from lib.database.abstract.Database import DatabaseABC
from config.models.user import UserModel
from config.enums.users.roles import UserRolesEnum
from config.models.messages import (
    ConversationInput,
    ConversationModel,
    ConversationResponseModel,
    MessageInput,
    MessageModel,
)
from services.users import get_user_from_token

router = APIRouter(dependencies=[Depends(get_user_from_token)],
    prefix="/api/messages",
    tags=["Messages"],
)

conversation_not_found = HTTPException(status_code=404, detail="Conversation not found.")
not_a_participant = HTTPException(status_code=403, detail="You are not a participant of this conversation.")


@router.post("/conversations", response_model=str,
             summary="Creates a conversation, optionally linked to a submission.")
def create_conversation(conversation : ConversationInput,
                        user : UserModel = Depends(get_user_from_token),
                        db : DatabaseABC = Depends(get_db)) -> str:
    """Creates a conversation with the given participants. The conversation can
    be linked to a submission (e.g. 'chat with owner') but can also be a general
    conversation between users. If the conversation is linked to a submission,
    only users with access to the submission can be added as participants."""
    if user.role < UserRolesEnum.STANDARD:
        raise HTTPException(status_code=403, detail="Guests cannot create conversations.")
    if user.tag not in conversation.user_tags:
        raise HTTPException(status_code=400, detail="The creator must be a participant of the conversation.")
    if conversation.submission_tag is not None:
        if not db.submissions.exists(tag = conversation.submission_tag):
            raise HTTPException(status_code=404, detail=f"Submission with tag {conversation.submission_tag} not found.")
        from services.submission import check_submission_tags_access
        check_submission_tags_access(conversation.submission_tag, user, db = db)
    conversation_tag = db.messages.insert_conversation(created_by = user.tag, conversation = conversation)
    if conversation_tag is None:
        raise HTTPException(status_code=400, detail="Conversation could not be created, check the participants.")
    return conversation_tag


@router.get("/conversations", response_model=List[ConversationResponseModel],
            summary="Returns the conversations of the current user.")
def get_my_conversations(submission_tag : Optional[str] = None,
                         user : UserModel = Depends(get_user_from_token),
                         db : DatabaseABC = Depends(get_db)) -> List[ConversationResponseModel]:
    return db.messages.get_conversations_for_user(user_tag = user.tag, submission_tag = submission_tag)


@router.get("/conversations/{conversation_tag}", response_model=ConversationModel,
            summary="Returns a conversation by tag. Requires participants only.")
def get_conversation(conversation_tag : str,
                     user : UserModel = Depends(get_user_from_token),
                     db : DatabaseABC = Depends(get_db)) -> ConversationModel:
    if not db.messages.exists(conversation_tag):
        raise conversation_not_found
    if not db.messages.is_participant(conversation_tag = conversation_tag, user_tag = user.tag):
        if user.role < UserRolesEnum.CURATOR:
            raise not_a_participant
    conversation = db.messages.get_conversation(conversation_tag)
    if conversation is None:
        raise conversation_not_found
    return conversation


@router.get("/conversations/{conversation_tag}/messages", response_model=List[MessageModel],
            summary="Returns the messages of a conversation. Requires a participant.")
def get_messages(conversation_tag : str,
                 limit : int = None,
                 user : UserModel = Depends(get_user_from_token),
                 db : DatabaseABC = Depends(get_db)) -> List[MessageModel]:
    if not db.messages.exists(conversation_tag):
        raise conversation_not_found
    if not db.messages.is_participant(conversation_tag = conversation_tag, user_tag = user.tag):
        if user.role < UserRolesEnum.CURATOR:
            raise not_a_participant
    db.messages.mark_read(conversation_tag = conversation_tag, user_tag = user.tag)
    return db.messages.get_messages(conversation_tag = conversation_tag, limit = limit)


@router.post("/conversations/{conversation_tag}/messages", response_model=str,
             summary="Adds a message to a conversation. Requires a participant.")
def post_message(conversation_tag : str,
                 message : MessageInput,
                 user : UserModel = Depends(get_user_from_token),
                 db : DatabaseABC = Depends(get_db)) -> str:
    if not db.messages.exists(conversation_tag):
        raise conversation_not_found
    if not db.messages.is_participant(conversation_tag = conversation_tag, user_tag = user.tag):
        raise not_a_participant
    message_tag = db.messages.insert_message(conversation_tag = conversation_tag, sender_tag = user.tag, message = message)
    if message_tag is None:
        raise conversation_not_found
    return message_tag


@router.post("/conversations/{conversation_tag}/read",
             summary="Marks the conversation as read for the current user.")
def mark_conversation_read(conversation_tag : str,
                           user : UserModel = Depends(get_user_from_token),
                           db : DatabaseABC = Depends(get_db)) -> bool:
    if not db.messages.exists(conversation_tag):
        raise conversation_not_found
    if not db.messages.is_participant(conversation_tag = conversation_tag, user_tag = user.tag):
        raise not_a_participant
    return db.messages.mark_read(conversation_tag = conversation_tag, user_tag = user.tag)


@router.get("/conversations/{conversation_tag}/unread",
            summary="Returns the number of unread messages of a conversation for the current user.")
def get_unread_count(conversation_tag : str,
                     user : UserModel = Depends(get_user_from_token),
                     db : DatabaseABC = Depends(get_db)) -> int:
    if not db.messages.exists(conversation_tag):
        raise conversation_not_found
    if not db.messages.is_participant(conversation_tag = conversation_tag, user_tag = user.tag):
        raise not_a_participant
    return db.messages.get_unread_count(conversation_tag = conversation_tag, user_tag = user.tag)


@router.get("/submissions/{submission_tag}/conversations", response_model=List[ConversationModel],
            summary="Returns the conversations linked to a submission. Requires submission access.")
def get_submission_conversations(submission_tag : str,
                                 user : UserModel = Depends(get_user_from_token),
                                 db : DatabaseABC = Depends(get_db)) -> List[ConversationModel]:
    from services.submission import check_submission_access
    check_submission_access(submission_tag = submission_tag, user = user, db = db)
    return db.messages.get_conversations_for_submission(submission_tag = submission_tag)

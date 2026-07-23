from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from typing import Dict, List, Literal
from services.users import is_user_admin, get_user_from_token
from services.mail import send_email_in_background

from lib.database.Database import Database


from config.models.user import UserModel
from config.models.protocols import InsertProtocolModel, UpdateProtocolModel, ProtocolBaseModel
from config.models.attributes import AttributeValueModel
from config.enums.users.roles import UserRolesEnum
from config.models.parameter import APIParamString
from config.models.calculations.quantile import QuantileModel

from config.settings.general import get_general_settings
from config.settings.email import get_email_settings
from config.models.permissions import PermissionResponseModel

GENERAL_SETTINGS = get_general_settings()
EMAIL_SETTINGS = get_email_settings()
router = APIRouter(
    prefix="/api/protocols",
    tags=["Protocols"]
    )

DB = Database.DB()

@router.get("/q", response_model=List[str])
def get_protocols(search_string : str = None, submission_tags : str = None,  limit : int = None, user : UserModel = Depends(get_user_from_token)) -> List[str]:
    "Returns the protocol tags that match the search string."
    return DB.protocols.find(search_string=search_string, submission_tags = APIParamString(param=submission_tags).param, limit=limit)

@router.get("/{protocol_tag}/submissions", response_model=List[str])
def get_protocol_submissions(protocol_tag : str, user : UserModel = Depends(get_user_from_token)) -> List[str]:
    "Returns the submission tags linked to the given protocol tag."
    return DB.protocols.get_submissions(tag=protocol_tag)

@router.get("/{protocol_tag}", response_model=ProtocolBaseModel)
def get_protocol(protocol_tag :str, user : UserModel = Depends(get_user_from_token)) -> ProtocolBaseModel:
    "Returns the protocol identified by the given tag."
    return DB.protocols.get(tag=protocol_tag)

@router.post("/", response_model=bool)
def insert_protocol(protocol : InsertProtocolModel, user : UserModel = Depends(get_user_from_token)) -> bool:
    "Inserts a new protocol. The tag is generated based on the title and protocol text."
    return DB.protocols.insert(title=protocol.title, protocol_text=protocol.text, user_tag=user.tag, doi=protocol.doi, pubmed_id=protocol.pubmed_id, url=protocol.url)

@router.post("/{protocol_tag}/link/{submission_tag}", response_model=bool)
def link_protocol_to_submission(protocol_tag : str, submission_tag : str, user : UserModel = Depends(get_user_from_token)) -> bool:
    "Links the given protocol to the specified submission."
    return DB.protocols.link(tag=protocol_tag, submission_tag=submission_tag, user_tag=user.tag)

@router.delete("/{protocol_tag}/link/{submission_tag}", response_model=bool)
def unlink_protocol_from_submission(protocol_tag : str, submission_tag : str, user : UserModel = Depends(get_user_from_token)) -> bool:
    "Unlinks the given protocol from the specified submission."
    return DB.protocols.unlink(tag=protocol_tag, submission_tag=submission_tag)


@router.patch("/{protocol_tag}", response_model=bool)
def update_protocol(protocol_tag : str, updated_protocol : UpdateProtocolModel, user : UserModel = Depends(get_user_from_token)) -> bool:
    "Updates the title and/or text of the specified protocol."
    return DB.protocols.update(tag=protocol_tag, title=updated_protocol.title, protocol_text=updated_protocol.text, user_tag=user.tag, doi=updated_protocol.doi, pubmed_id=updated_protocol.pubmed_id, url=updated_protocol.url)







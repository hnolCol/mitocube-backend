from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from typing import List
from services.users import is_user_admin, get_user_from_token
from services.mail import send_email_in_background
from lib.data.database_helper.ABCDatabaseHelper import MCDatabaseHelper
from lib.database.Database import Database


from config.models.user import UserModel
from config.models.attributes import AttributeValueModel
from config.enums.states import SubmissionStatesEnums
from config.models.parameter import APIParamString

from config.settings.general import get_general_settings
from config.settings.email import get_email_settings


GENERAL_SETTINGS = get_general_settings()
EMAIL_SETTINGS = get_email_settings()

router = APIRouter(
    prefix="/api/unittypes",
    tags=["Unit Types"]
    )

DB = Database.DB()


@router.get("")
def get_unit_types(user : UserModel = Depends(is_user_admin)):
    ""

    
@router.get("/{unit_type_tag}/units") #maybe remove the /units since is no balnk end? 
def get_units_for_unit_type(unit_type_tag : str):
    "" 
    units = DB.unittypes.get_units(tags=[unit_type_tag])
    if len(units)!= 1: 
        raise HTTPException(status_code=404,detail="No units found for this unit type in the database.")
    return units[0]
    


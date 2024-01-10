from fastapi import APIRouter, Depends
from typing import List


from services.users import is_user_admin, get_user_from_token
from config.models.user import UserModel
from config.models.info.info import InfoResponse
from config.settings.general import get_general_settings

GENERAL_SETTINGS  = get_general_settings()


router = APIRouter(
    prefix="/api",
    tags=["App Information"],
    )



@router.get("/info/app",summary="Returns basic information about the app.", response_model=InfoResponse)
def get_application_info(user : UserModel = Depends(get_user_from_token)):
    """"""
    return InfoResponse(
        app_name=GENERAL_SETTINGS.app_name, 
        version=GENERAL_SETTINGS.version, 
        lead_contact=GENERAL_SETTINGS.lead_contact, 
        app_description=GENERAL_SETTINGS.description
        )


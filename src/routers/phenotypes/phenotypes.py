from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from typing import List
from services.users import is_user_admin, get_user_from_token
from services.mail import send_email_in_background
from lib.data.database_helper.ABCDatabaseHelper import MCDatabaseHelper
from lib.database.Database import Database


from config.models.user import UserModel
from config.models.phenotype import PhenotypeGenotypeInput, PhenotypeModel, PhenotypeInputModel
from config.enums.states import SubmissionStatesEnums
from config.models.parameter import APIParamString

from config.settings.general import get_general_settings
from config.settings.email import get_email_settings


GENERAL_SETTINGS = get_general_settings()
EMAIL_SETTINGS = get_email_settings()
router = APIRouter(
    prefix="/api/phenotypes",
    tags=["Phenotypes"]
    )

DB = Database.DB()


@router.get("")
def get_phenotype(query : str = None, limit : int = 20, user : UserModel = Depends(get_user_from_token)) -> List[PhenotypeModel]:
    ""
    if query is not None:
        return DB.phenotypes.find(query = query, limit = limit)
        
    return DB.phenotypes.get(limit = limit)
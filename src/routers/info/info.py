from fastapi import APIRouter, Depends
from typing import List
from collections import OrderedDict

from services.users import is_user_admin, get_user_from_token

from config.models.user import UserModel
from config.models.info.info import InfoResponse
from config.settings.general import get_general_settings
from config.settings.keyfigures import get_key_figure_settings
from lib.data.database_helper.ABCDatabaseHelper import MCDatabaseHelper
from lib.user.UserHandling import UserDB

GENERAL_SETTINGS  = get_general_settings()
KEY_FIGURE_SETTINGS = get_key_figure_settings()

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




@router.get("/info/keyfigures",summary="Returns the key figures of the backend")
def get_keyfigures(user : UserModel = Depends(get_user_from_token)):
    """Returns the defined key figures that are defined 
    in the corresponding settings.

    Parameters
    ----------
    user : UserModel, optional
        the user that is inferred from the token, by default Depends(get_user_from_token)
    """
    db_helper = MCDatabaseHelper.getDatabaseHelper()
    key_figures = OrderedDict()
    if KEY_FIGURE_SETTINGS.number_submissions:
        key_figures["Submissions"] = len(db_helper.get_all_labels())
    if KEY_FIGURE_SETTINGS.number_published_datasets:
        key_figures["Published Data"] = db_helper.get_datatable_count()
    if KEY_FIGURE_SETTINGS.number_proteins:
        key_figures["Proteins"] = db_helper.get_number_features()
    if KEY_FIGURE_SETTINGS.number_users:
        key_figures["Users"] = UserDB.get_number_of_users()
    return [{"label" : k, "metric" : v} for k,v in key_figures.items()]
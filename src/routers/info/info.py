from fastapi import APIRouter, Depends
from typing import List
from collections import OrderedDict
import json 

from services.users import is_user_admin, get_user_from_token
from services.json import read_json 

from config.models.user import UserModel
from config.models.info.info import InfoResponse
from config.settings.general import get_general_settings
from config.settings.keyfigures import get_key_figure_settings
from lib.data.database_helper.ABCDatabaseHelper import MCDatabaseHelper
from lib.user.UserHandling import UserDB

from config.enums.states import SubmissionStatesEnums

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
        published_datasets = db_helper.get_label_count_by_state(k_subset=set([SubmissionStatesEnums.ACTIVE]))
        if SubmissionStatesEnums.ACTIVE in published_datasets:
            key_figures["Published Data"] = published_datasets[SubmissionStatesEnums.ACTIVE]["submission_count"] 
    if KEY_FIGURE_SETTINGS.number_proteins:
        key_figures["Proteins"] = db_helper.get_number_features()
    if KEY_FIGURE_SETTINGS.number_genotypes:
        key_figures["Genotypes"] = db_helper.get_number_genotypes()
    if KEY_FIGURE_SETTINGS.number_users:
        key_figures["Users"] = UserDB.get_number_of_users()
    return [{"label" : k, "metric" : v} for k,v in key_figures.items()]



@router.get("/info/terms")
def get_terms_of_use(user : UserModel = Depends(get_user_from_token)):
    path_to_file = GENERAL_SETTINGS.use_terms_file 
    use_of_terms = read_json(path_to_file)
    return use_of_terms
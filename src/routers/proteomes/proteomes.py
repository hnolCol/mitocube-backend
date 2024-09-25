from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from typing import List
from services.users import is_user_admin, get_user_from_token
from services.mail import send_email_in_background
from lib.data.database_helper.ABCDatabaseHelper import MCDatabaseHelper
from lib.data.database.Database import Database


from config.models.user import UserModel
from config.models.attributes import AttributeValueModel
from config.enums.states import SubmissionStatesEnums
from config.models.parameter import APIParamString

from config.settings.general import get_general_settings
from config.settings.email import get_email_settings


GENERAL_SETTINGS = get_general_settings()
EMAIL_SETTINGS = get_email_settings()
router = APIRouter(
    prefix="/api/proteomes",
    tags=["Proteomes"]
    )

DB = Database.DB()


@router.get("")
def get_proteomes(user : UserModel = Depends(is_user_admin)):
    ""
    return DB.proteomes.get()



@router.post("")
def add_protein_by_proteome_tag(background_task : BackgroundTasks, proteome_tag: str, reviewed : bool = True, user : UserModel = Depends(is_user_admin)):
    """Adds proteins from Uniprot
    including the annotations and sequence information.

    Parameters
    ----------
    proteome_id : str
        The Uniprot proteome tag.
    user : UserModel, optional
        The user that added the proteome to the database, by default Depends(is_user_admin)
    """
    try:
        N = DB.proteomes.insert_uniprot_proteome(proteome_tags=APIParamString(param=proteome_tag).param, reviewed  = reviewed, user_tag = user.tag)
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500,detail="There was an error when retrieving data from Uniprot.")
    
    send_email_in_background(background_tasks=background_task,
                             subject=f"Proteome {proteome_tag} added.",
                             email_to=[user.email],
                             include_setting_cc=True,
                             body={
                                 "app_name" : GENERAL_SETTINGS.app_name,
                                 "first_name" : user.firstname,
                                 "proteome_tag" : proteome_tag,
                                 "n_proteins" : N
                                 
                             },
                             template_mame=EMAIL_SETTINGS.mail_proteome_added_template)
    
    
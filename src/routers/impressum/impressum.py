from fastapi import APIRouter, Depends, HTTPException
from lib.database.Database import get_db
from lib.database.abstract.Database import DatabaseABC

from config.models.user import UserModel
from config.models.Impressum import ImpressumModel, ImpressumUpdateModel
from services.users import get_user_from_token, is_user_admin
from config.settings.general import get_general_settings


GENERAL_SETTINGS = get_general_settings()


def get_default_impressum_text() -> str:
    "Builds the default impressum text from the .env driven general settings."
    return (
        f"{GENERAL_SETTINGS.app_name}\n"
        f"\n"
        f"{GENERAL_SETTINGS.lead_contact_institute}\n"
        f"{GENERAL_SETTINGS.lead_contact_group}\n"
        f"\n"
        f"Contact:\n"
        f"{GENERAL_SETTINGS.lead_contact_first_name} {GENERAL_SETTINGS.lead_contact_last_name}\n"
        f"{GENERAL_SETTINGS.lead_contact}\n"
        f"{GENERAL_SETTINGS.url}\n"
    )


router = APIRouter(
    prefix="/api/impressum",
    tags=["Impressum"]
)


@router.get("", response_model=ImpressumModel)
def get_impressum(user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> ImpressumModel:
    "Returns the current impressum. If none exists yet, a default based on the environment settings is created."
    impressum = db.impressum.get()
    if impressum is None:
        default = ImpressumUpdateModel(title="Impressum", text=get_default_impressum_text())
        impressum = db.impressum.update(impressum=default, user_tag="system")
    return impressum


@router.put("", summary="Create or update the impressum. Requires admin rights.")
def update_impressum(impressum : ImpressumUpdateModel, user : UserModel = Depends(is_user_admin), db : DatabaseABC = Depends(get_db)) -> ImpressumModel:
    return db.impressum.update(impressum=impressum, user_tag=user.tag)

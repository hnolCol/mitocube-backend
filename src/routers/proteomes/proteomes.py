from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from typing import Dict, List, Literal
from services.users import is_user_admin, get_user_from_token
from services.mail import send_email_in_background

from lib.database.Database import Database


from config.models.user import UserModel
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
    prefix="/api/proteomes",
    tags=["Proteomes"]
    )

DB = Database.DB()


@router.get("/q", response_model=List[str])
def get_proteomes(search_string : str, limit : int = None, user : UserModel = Depends(get_user_from_token)) -> List[str]:
    "Returns the proteome tags that match the search string."
    return DB.proteomes.find(search_string=search_string, limit=limit)


@router.get("/count", response_model=int)
def get_proteome_count(user : UserModel = Depends(get_user_from_token)) -> int:
    "Returns the number of proteomes in the database."
    return DB.proteomes.count()

@router.get("/permissions", response_model=PermissionResponseModel)
def get_proteome_permissions(user : UserModel = Depends(get_user_from_token)) -> PermissionResponseModel:
    "Returns the permissions for all proteomes. Either the user can create/write all proteomes or none."
    
    return PermissionResponseModel(
        user_tag = user.tag, 
        role = user.role,
        create=user.role >= UserRolesEnum.CURATOR,
        update=user.role >= UserRolesEnum.CURATOR
    )

@router.get("/{proteome_tag}")
def get_proteome_by_tag(proteome_tag : str, user : UserModel = Depends(get_user_from_token)) -> Dict:
    "Returns the proteome information for the given proteome tag."
    if not DB.proteomes.exists(tag=proteome_tag):
        raise HTTPException(status_code=404, detail="Proteome not found.")
    return DB.proteomes.get(tag=proteome_tag)

@router.get("/{proteome_tag}/text")
def get_proteome_by_tag(proteome_tag : str, user : UserModel = Depends(get_user_from_token)) -> str:
    "Returns the proteome information for the given proteome tag."
    if not DB.proteomes.exists(tag=proteome_tag):
        raise HTTPException(status_code=404, detail="Proteome not found.")
    return DB.proteomes.get_text(tag=proteome_tag)

@router.get("/{proteome_tag}/is_updating", response_model=bool)
def get_proteome_state(proteome_tag : str, user : UserModel = Depends(get_user_from_token)) -> bool:
    "Returns the proteome state (e.g. is updating or ready) for the given proteome tag."
    if not DB.proteomes.exists(tag=proteome_tag):
        raise HTTPException(status_code=404, detail="Proteome not found.")
    is_updating = DB.proteomes.is_updating(tag=proteome_tag)
    return is_updating if is_updating is not None else False


@router.get("/{proteome_tag}/created_at")
def get_proteome_created_at(proteome_tag : str, user : UserModel = Depends(get_user_from_token)) -> float|int:
    "Returns the proteome created_at (e.g. is updating or ready) for the given proteome tag."
    if not DB.proteomes.exists(tag=proteome_tag):
        raise HTTPException(status_code=404, detail="Proteome not found.")
    return DB.proteomes.get_created_at(tag=proteome_tag)


@router.get("/{proteome_tag}/proteins/count", response_model=int)
def get_proteome_protein_count(proteome_tag : str, user : UserModel = Depends(get_user_from_token)) -> int:
    "Returns the number of proteins for the given proteome tag."
    if not DB.proteomes.exists(tag=proteome_tag):
        raise HTTPException(status_code=404, detail="Proteome not found.")
    return DB.proteomes.get_protein_count(tag=proteome_tag)


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
                             template_name=EMAIL_SETTINGS.mail_proteome_added_template)
    
    return {"message" : f"The proteome {proteome_tag} was added with {N} proteins."}
    
@router.get("/{proteome_tag}/correlation/{feature_tag}")
def get_feature_correlation_across_proteome(proteome_tag : str, feature_tag : str , filter_tag : str = None, direction : Literal["positive","negative","both"] = "positive", min_data_points : int = 5, limit : int = 20) -> List:
    "" 
    if not DB.features.exists(tag=feature_tag):
        raise HTTPException(status_code=404,detail=f"The feature was not found {feature_tag}")
    
    submission_tags = DB.submission_filter.filter_by_attribute_value_tags(attribute_value_tags = [proteome_tag])
    submission_tags = [tag for tag in submission_tags if DB.submission_has_dataset(tag = tag)]
    
    
    if len(submission_tags) == 0: raise HTTPException(status_code=404,detail=f"No submission tag with datatables found of the proteome_tag {proteome_tag}.")
    correlated_features = DB.submissions.get_correlated_features(tags = submission_tags,
                                           feature_tag = feature_tag,
                                           filter_tag = filter_tag,
                                           direction = direction,
                                           limit = limit,
                                           min_data_points = min_data_points)
    return correlated_features.to_dict(orient="records")
    
    
@router.get("/{proteome_tag}/abundance")
def get_proteome_abundance(proteome_tag : str) -> QuantileModel:
    if not DB.proteomes.exist(tags = proteome_tag): raise HTTPException(status_code=404, detail="Proteome not found.")
    
    qs = DB.proteomes.get_feature_abundance_dist(tag = proteome_tag)
    return qs 
    
    
    
    
    
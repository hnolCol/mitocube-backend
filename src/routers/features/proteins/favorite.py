from fastapi import APIRouter, Depends
from typing import List

# 
from lib.database.Database import Database

from config.models.user import UserModel

from config.models.parameter import APIParamString
from services.users import is_user_admin, get_user_from_token, is_user_at_least_curator

DB = Database.DB()


router = APIRouter(
    prefix="/api/features/proteins",
    tags=["Features", "Proteins"]
    )


@router.get("/favorites", summary="Returns the overall favorite proteins.")
def get_favorite_proteins(submission_tags : str = None, annotation_tags : str = None, proteome_tags : str = None, limit : int = None, user: UserModel = Depends(get_user_from_token)) -> List[str]:
    """
    Returns the overall favorite proteins. This is based on how often a protein is quantified across all submissions.
    
    Parameters
    ----------
    submission_tags : str, optional
        Semicolon separated submission tags to filter the search (e.g. proteins quantified in specific submissions), by default None
    annotation_tags : str, optional
        Semicolon separated annotation tags to filter the search (e.g. proteins that are annotated with specific annotations), by default None
    proteome_tags : str, optional
        Semicolon separated proteome tags to filter the search (e.g. proteins that are part of specific proteomes), by default None
    limit : int, optional
        The limit of proteins to return, by default None
    user : UserModel, optional
        The user that is extracted by the token, by default Depends(get_user_from_token)
    Returns
    -------
    List[str]
        A list of favorite protein tags.
    """
    return DB.proteins.get_favorite_proteins(
        limit = limit,
        submission_tags=APIParamString(param=submission_tags).param, 
        annotation_tags=APIParamString(param=annotation_tags).param, 
        proteome_tags=APIParamString(param=proteome_tags).param,
        user_tag=user.tag)
    


@router.get("/favorites/{protein_tag}", summary="Returns if the user favors a specific protein. User is inferred by token.")
def get_favorite_proteins(protein_tag : str, user: UserModel = Depends(get_user_from_token)) -> bool:
    """
    Returns if the user favors a specific protein. User is inferred by token.
    
    Parameters
    ----------
    protein_tag : str
        The tag of the protein to check.
    user : UserModel, optional
        The user that is extracted by the token, by default Depends(get_user_from_token)
    Returns
    -------
    bool
        True if the protein is favored by the user, False otherwise.
    """
    return DB.proteins.is_protein_favorite(protein_tag=protein_tag, user_tag=user.tag)


@router.post("/favorites/{protein_tag}", summary="Indicating that the user favors a specific protein.")
def bulk_insert_protein_features(protein_tag : str, remove_if_exists : bool = True, user: UserModel = Depends(get_user_from_token)) -> bool:
    """
    Bulk insert of new protein features. Requires curator rights.
    
    Parameters
    ----------
    protein_tag : str
        The tag of the protein to favor.
    remove_if_exists : bool, optional
        Whether to remove the protein from favorites if it already exists, by default True
    user : UserModel, optional
        The user that is extracted by the token, by default Depends(is_user_at_least_curator)
    
    Returns
    -------
    bool
        Indicates whether the protein was successfully favored or removed from favorites.
    """
    if remove_if_exists and DB.proteins.is_protein_favorite(protein_tag=protein_tag, user_tag=user.tag):
        return DB.proteins.remove_favorite_protein(protein_tag=protein_tag, user_tag=user.tag)
    return DB.proteins.set_favorite_protein(protein_tag=protein_tag, user_tag=user.tag)
    
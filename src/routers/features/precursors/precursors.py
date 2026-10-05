from fastapi import APIRouter, Depends, HTTPException
from config.models.user import UserModel
from services.users import get_user_from_token
from lib.database.Database import Database
from config.models.parameter import APIParamString

DB = Database.DB()

router = APIRouter(
    prefix="/api/features/precursors",
    tags=["Features", "Precursors"]
)


@router.get("/q", summary="Finds precursors by search query.")
def find_precursors_by_query(search_string : str, limit : int = 50, submission_tags : str = None, user: UserModel = Depends(get_user_from_token)):
    """
    Finds precursors by their tag (sequence followed by charge state, e.g. PEPTIDEK.2).

    Parameters
    ----------
    search_string : str
        The search string to match against the precursor tags.
    limit : int, optional
        The limit of precursors to return, by default 50
    submission_tags : str, optional
        Semicolon separated submission tags to filter the search (e.g. precursors quantified in specific submissions), by default None
    user : UserModel, optional
        The user that is extracted by the token, by default Depends(get_user_from_token)

    Returns
    -------
    List[str]
        Precursor tags
    """
    submission_tags = APIParamString(param=submission_tags).param
    return DB.precursors.find(search_string=search_string, limit=limit, submission_tag=submission_tags[0] if submission_tags else None)


@router.get("/{precursor_tag}")
def get_precursor_by_tag(precursor_tag : str):
    """
    Retrieves a precursor by its tag.

    Parameters
    ----------
    precursor_tag : str
        The tag of the precursor to retrieve.

    Returns
    -------
    PrecursorResponseModel
        The precursor data.

    Raises
    ------
    HTTPException
        If the precursor with the given tag does not exist.
    """
    if not DB.precursors.exists(tag = precursor_tag): raise HTTPException(status_code=404, detail="Precursor not found.")
    return DB.precursors.get(tag = precursor_tag)


@router.get("/{precursor_tag}/abundance")
def get_precursor_abundance_by_tag(precursor_tag : str, submission_tags : str = None, user : UserModel = Depends(get_user_from_token)):
    """
    Retrieves the abundance of a precursor by its tag.

    Parameters
    ----------
    precursor_tag : str
        The tag of the precursor to retrieve.
    submission_tags : str, optional
        Semicolon separated submission tags to filter the abundance data, by default None (all submissions)
    user : UserModel, optional
        The user making the request, by default Depends(get_user_from_token)

    Returns
    -------
    pd.DataFrame
        The abundance data of the precursor.

    Raises
    ------
    HTTPException
        If the precursor with the given tag does not exist.
    """
    if not DB.precursors.exists(tag = precursor_tag): raise HTTPException(status_code=404, detail="Precursor not found.")
    return DB.precursors.get_abundance(tag = precursor_tag, submission_tags = APIParamString(submission_tags).param)


@router.get("/{precursor_tag}/is_quantified")
def get_precursor_is_quantified(precursor_tag : str, user : UserModel = Depends(get_user_from_token)):
    """
    Checks if a precursor is quantified.

    Parameters
    ----------
    precursor_tag : str
        The tag of the precursor to check.
    user : UserModel, optional
        The user making the request, by default Depends(get_user_from_token)

    Returns
    -------
    bool
        True if the precursor is quantified, False otherwise.

    Raises
    ------
    HTTPException
        If the precursor with the given tag does not exist.
    """
    if not DB.precursors.exists(tag = precursor_tag): raise HTTPException(status_code=404, detail="Precursor not found.")
    return DB.precursors.is_quantified(precursor_tag = precursor_tag)

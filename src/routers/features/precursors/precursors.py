from fastapi import APIRouter, Depends, HTTPException
from typing import List
from config.models.user import UserModel
from config.models.precursors import PrecursorInsertModel, PrecursorResponseModel
from services.users import is_user_at_least_curator, get_user_from_token
from lib.database.Database import Database
from config.models.parameter import APIParamString

DB = Database.DB()

router = APIRouter(dependencies=[Depends(get_user_from_token)],
    prefix="/api/features/precursors",
    tags=["Features", "Precursors"]
)


@router.get("/q", summary="Finds precursors by search query.")
def find_precursors_by_query(search_string : str, limit : int = 50, submission_tags : str = None, user: UserModel = Depends(get_user_from_token)) -> List[str]:
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


@router.get("/{precursor_tag}", summary="Retrieves a precursor by its tag.")
def get_precursor_by_tag(precursor_tag : str, user : UserModel = Depends(get_user_from_token)) -> PrecursorResponseModel:
    """
    Retrieves a precursor by its tag. The protein_group_tag is the protein group
    associated with the precursor that has the least proteins connected to itself
    (e.g. the protein group consisting of a single protein). All associated protein
    groups are returned in protein_group_tags.

    Parameters
    ----------
    precursor_tag : str
        The tag of the precursor to retrieve.
    user : UserModel, optional
        The user making the request, by default Depends(get_user_from_token)

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


@router.get("/{precursor_tag}/abundance", summary="Retrieves the abundance of a precursor by its tag.")
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


@router.get("/{precursor_tag}/is_quantified", summary="Checks if a precursor is quantified.")
def get_precursor_is_quantified(precursor_tag : str, user : UserModel = Depends(get_user_from_token)) -> bool:
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


@router.get("/protein_groups/{protein_group_tag}", summary="Retrieves all precursors of a protein group.")
def get_precursors_by_protein_group(protein_group_tag : str, submission_tag : str = None, limit : int = None, user : UserModel = Depends(get_user_from_token)) -> List[PrecursorResponseModel]:
    """
    Retrieves all precursors associated with a given protein group. If a submission tag is
    given, only precursors quantified in that submission are returned.

    Parameters
    ----------
    protein_group_tag : str
        The tag of the protein group to retrieve precursors for.
    submission_tag : str, optional
        The tag of the submission to filter the precursors by, by default None
    limit : int, optional
        The maximum number of results to return, by default None
    user : UserModel, optional
        The user making the request, by default Depends(get_user_from_token)

    Returns
    -------
    List[PrecursorResponseModel]
        The precursor data. The protein_group_tag is the requested protein group tag.

    Raises
    ------
    HTTPException
        If the protein group with the given tag does not exist.
    """
    if not DB.protein_groups.exists(tag = protein_group_tag):
        raise HTTPException(status_code=404, detail=f"Protein group with tag {protein_group_tag} not found.")
    return DB.precursors.get_by_protein_group(protein_group_tag = protein_group_tag, submission_tag = submission_tag, limit = limit)

from fastapi import APIRouter, Depends, HTTPException
from config.models.user import UserModel
from services.users import get_user_from_token
from lib.database.Database import Database

DB = Database.DB()

router = APIRouter(
    prefix="/api/features/precursors",
    tags=["Features", "Precursors"]
)


@router.get("/count", summary="Counts the number of precursors.")
def count_precursors(submission_tag : str = None, user : UserModel = Depends(get_user_from_token)) -> int:
    """
    Counts the number of precursors. If a submission tag is given, only precursors
    quantified in that submission are counted.

    Parameters
    ----------
    submission_tag : str, optional
        The tag of the submission to count precursors for, by default None
    user : UserModel, optional
        The user making the request, by default Depends(get_user_from_token)

    Returns
    -------
    int
        The number of precursors.

    Raises
    ------
    HTTPException
        If the submission with the given tag does not exist.
    """
    if submission_tag is not None and not DB.submissions.exists(tag = submission_tag):
        raise HTTPException(status_code=404, detail=f"Submission with tag {submission_tag} not found.")
    return DB.precursors.count(submission_tag = submission_tag)

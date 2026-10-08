from fastapi import APIRouter, Depends, HTTPException
from lib.database.Database import get_db
from lib.database.abstract.Database import DatabaseABC
from config.models.user import UserModel
from services.users import get_user_from_token


router = APIRouter(dependencies=[Depends(get_user_from_token)],
    prefix="/api/features/precursors",
    tags=["Features", "Precursors"]
)


@router.get("/count", summary="Counts the number of precursors.")
def count_precursors(submission_tag : str = None, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> int:
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
    if submission_tag is not None and not db.submissions.exists(tag = submission_tag):
        raise HTTPException(status_code=404, detail=f"Submission with tag {submission_tag} not found.")
    return db.precursors.count(submission_tag = submission_tag)


@router.get("/protein_groups/{protein_group_tag}/count", summary="Counts the number of precursors of a protein group.")
def count_precursors_by_protein_group(protein_group_tag : str, submission_tag : str = None, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> int:
    """
    Counts the number of precursors associated with a given protein group. If a submission
    tag is given, only precursors quantified in that submission are counted.

    Parameters
    ----------
    protein_group_tag : str
        The tag of the protein group to count precursors for.
    submission_tag : str, optional
        The tag of the submission to count precursors for, by default None
    user : UserModel, optional
        The user making the request, by default Depends(get_user_from_token)

    Returns
    -------
    int
        The number of precursors of the protein group.

    Raises
    ------
    HTTPException
        If the protein group or the submission with the given tag does not exist.
    """
    if not db.protein_groups.exists(tag = protein_group_tag):
        raise HTTPException(status_code=404, detail=f"Protein group with tag {protein_group_tag} not found.")
    if submission_tag is not None and not db.submissions.exists(tag = submission_tag):
        raise HTTPException(status_code=404, detail=f"Submission with tag {submission_tag} not found.")
    return db.precursors.count_by_protein_group(protein_group_tag = protein_group_tag, submission_tag = submission_tag)

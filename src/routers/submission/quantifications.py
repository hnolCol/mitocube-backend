from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Query
from lib.database.Database import Database
from config.models.user import UserModel
from config.models.submissions.quantifications import ProteinQuantificationModel, PrecursorQuantificationModel, ProteinQuantificationBulkInsertModel
from config.exceptions.HTTPExceptions import submission_tag_not_found
from services.users import get_user_from_token, is_user_at_least_curator
from typing import Dict, List, Literal

DB = Database.DB()

router = APIRouter(
    prefix="/api/submissions",
    tags=["Submission"],
    )

from pydantic import BaseModel

class ProteinQuantificationListModel(BaseModel):
    quantifications: List[ProteinQuantificationModel]
    
    
    
@router.get("/{submission_tag}/quantifications/exists", summary="Checks if quantification data for this submission exists.")
def get_submission_quant_exists(submission_tag : str, quantification_type :  Literal["proteins","protein_groups","precursors","any"], user : UserModel = Depends(get_user_from_token)) -> bool:
    """
    Checks if quantification data for this submission exists.

    Parameters
    ----------
    submission_tag : str
        The tag of the submission.  
    user : UserModel, optional
        The user that is extracted by the token, by default Depends(get_user_from_token)
    Returns
    -------
    bool
        True if quantification data exists, False otherwise.
    """

    if DB.submissions.exists(tag=submission_tag) is False:
        raise submission_tag_not_found

    return DB.submissions.quantification_exists(tag=submission_tag, type=quantification_type)

@router.post("/{submission_tag}/quantifications/proteins", summary="Insert protein quantifications for a given submission. Requires curator rights.")
def insert_protein_quantifications(
    submission_tag: str,
    quantifications: ProteinQuantificationListModel,
    user: UserModel = Depends(is_user_at_least_curator)
) -> int:
    """
    Insert protein quantifications for a given submission. Requires curator rights.

    Parameters
    ----------
    submission_tag : str
        The tag of the submission.  
    quantification_list : ProteinQuantificationListModel
        Object containing a list of protein quantifications to insert.
    user : UserModel, optional
        The user that is extracted by the token, by default Depends(get_user_from_token)
    Returns
    -------
    int
        Number of inserted protein quantifications.
    """

    print(quantifications)
    if DB.submissions.exists(tag=submission_tag) is False:
        raise HTTPException(status_code=404, detail="Submission not found")

    return DB.submissions.insert_protein_quantifications(submission_tag=submission_tag, quantifications=quantifications)





@router.post("/{submission_tag}/quantifications/proteins/precursors", summary="Bulk insert of precursor quantifications for a given submission. Requires curator rights.")
def insert_precursor_quantifications(
    submission_tag: str,
    quantifications: List[PrecursorQuantificationModel],
    user: UserModel = Depends(is_user_at_least_curator)
) -> int:
    """
    Bulk insert of precursor quantifications for a given submission. Requires curator rights.

    Parameters
    ----------
    submission_tag : str
        The tag of the submission.  
    quantifications : List[PrecursorQuantificationModel]
        List of precursor quantifications to insert.
    user : UserModel, optional
        The user that is extracted by the token, by default Depends(get_user_from_token)
    Returns
    -------
    int
        Number of inserted precursor quantifications.
    """

    if DB.submissions.exists(tag=submission_tag) is False:
        raise HTTPException(status_code=404, detail="Submission not found")

    return DB.submissions.insert_precursor_quantifications(submission_tag=submission_tag, quantifications=quantifications)
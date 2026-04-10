from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Query
from lib.database.Database import Database
from config.models.user import UserModel
from config.models.submissions.quantifications import ProteinGroupQuantificationModel, PrecursorQuantificationModel, ProteinQuantificationBulkInsertModel
from config.exceptions.HTTPExceptions import submission_tag_not_found
from services.users import get_user_from_token, is_user_at_least_curator
from typing import Dict, List, Literal
import numpy as np 
DB = Database.DB()

router = APIRouter(
    prefix="/api/submissions",
    tags=["Submission"],
    )

from pydantic import BaseModel

class ProteinGroupQuantificationListModel(BaseModel):
    quantifications: List[ProteinGroupQuantificationModel]
    
    
class ProteinGroupQuantificationCountModel(BaseModel):
    submission_tag: str
    count: int
    user_tag : str
    created_at : float
    
@router.get("/quantifications/protein_groups/count", summary="Get the number of protein group quantifications for a given submission.")
def get_protein_group_quantification_count(user : UserModel = Depends(get_user_from_token)) -> List[ProteinGroupQuantificationCountModel]:
    """
    Get the number of protein group quantifications for a given submission.

    Parameters
    ----------
    user : UserModel, optional
        The user that is extracted by the token, by default Depends(get_user_from_token)
    Returns
    -------
    List[ProteinGroupQuantificationCountModel]
        A list of ProteinGroupQuantificationCountModel objects, each containing the submission tag, the number of protein group quantifications, and the user tag of the creator of the submission.
    """

    return [ProteinGroupQuantificationCountModel(**record) for record in DB.submissions.get_protein_group_quantification_count().to_dict(orient="records")]
    
    
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
    quantifications: ProteinQuantificationBulkInsertModel,
    apply_statistics : bool = False,
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

    if DB.submissions.exists(tag=submission_tag) is False:
        raise HTTPException(status_code=404, detail="Submission not found")

    ##first check if all proteins exist
    N = DB.protein_groups.insert_bulk(protein_groups=set([q.tag for q in quantifications.quantifications]))
    num_quantifications = DB.submissions.insert_protein_quantifications(tag=submission_tag, quantifications=[q for q in quantifications.model_dump().get("quantifications", []) if np.isfinite(q["value"])])
    #if num_quantifications != len(quantifications.quantifications):
    if apply_statistics:
        print("Calculating statistics...")
        DB.submissions.calculate_multiple_comparison_metrices(tag = submission_tag)
        DB.submissions.transform_quantification_to_zscore_along_protein_groups(tag = submission_tag)
        DB.submissions.transform_quantification_to_zscore_along_samples(tag = submission_tag)

    return num_quantifications



@router.patch("/{submission_tag}/protein_groups/statistics", summary="Calculate and insert the statistics for the protein groups of a given submission. Requires curator rights.")
def calculate_protein_group_statistics(submission_tag : str, user : UserModel = Depends(is_user_at_least_curator)):
    """
    Calculate and insert the statistics for the protein groups of a given submission. Requires curator rights.

    Parameters
    ----------
    submission_tag : str
        The tag of the submission.  
    user : UserModel, optional
        The user that is extracted by the token, by default Depends(get_user_from_token)
    Returns
    -------
    bool
        True if the statistics were calculated and inserted successfully, False otherwise.
    """

    if DB.submissions.exists(tag=submission_tag) is False:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    ok = DB.submissions.remove_multiple_comparison_metrices(tag = submission_tag)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to remove existing statistics. Aborting calculation of new statistics.")
    DB.submissions.calculate_multiple_comparison_metrices(tag = submission_tag)
    DB.submissions.transform_quantification_to_zscore_along_protein_groups(tag = submission_tag)
    DB.submissions.transform_quantification_to_zscore_along_samples(tag = submission_tag)
    return True

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
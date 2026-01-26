from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Query
from lib.database.Database import Database
from config.models.user import UserModel
from config.enums.states import SubmissionStatesEnums
from services.users import get_user_from_token

from typing import List, Dict
DB = Database.DB()

router = APIRouter(
    prefix="/api/submissions/counts",
    tags=["Submission"],
    )

@router.get("/states/{state_tag}")
def get_submission_state_count(state_tag : SubmissionStatesEnums, user : UserModel = Depends(get_user_from_token)) -> int:
    "Return the number of submissions in a given state" #move to states router? 
    return DB.submissions.count(state=state_tag)


@router.get("/{submission_tag}/protein_groups") 
def get_protein_count_for_submission(submission_tag : str, user : UserModel = Depends(get_user_from_token)) -> int:
    "Return the number of protein groups for a given submission"
    if DB.submissions.exists(tag=submission_tag) is False:
        raise HTTPException(status_code=404, detail="Submission not found")
    return DB.protein_groups.count(submission_tag=submission_tag)


@router.get("/{submission_tag}/peptides") 
def get_peptide_count_for_submission(submission_tag : str, user : UserModel = Depends(get_user_from_token)) -> int:
    "Return the number of peptides for a given submission"
    if DB.submissions.exists(tag=submission_tag) is False:
        raise HTTPException(status_code=404, detail="Submission not found")
    return DB.peptides.count(submission_tag=submission_tag)


@router.get("/{submission_tag}/samples")
def get_sample_count_for_submission(submission_tag : str, user : UserModel = Depends(get_user_from_token)) -> int:
    "Return the number of samples for a given submission"
    if DB.submissions.exists(tag=submission_tag) is False:
        raise HTTPException(status_code=404, detail="Submission not found")
    return DB.samples.count(submission_tag=submission_tag)


@router.get("/{submission_tag}/samples/protein_groups")
def get_sample_protein_group_count_for_submission(submission_tag : str, user : UserModel = Depends(get_user_from_token)) -> List[Dict]:
    "Return the number of protein groups per sample for a given submission"
    if DB.submissions.exists(tag=submission_tag) is False:
        raise HTTPException(status_code=404, detail="Submission not found")
    sample_tags = DB.submissions.get_samples(tag = submission_tag)
    return [{"tag" : sample_tag, "count" : DB.samples.count_quantified_protein_groups(tag=sample_tag, submission_tag = submission_tag)} for sample_tag in sample_tags]
    
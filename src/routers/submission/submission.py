from fastapi import APIRouter, Depends
from typing import List, Annotated

from lib.data.database.ABCDatabase import MCDatabase 

from config.settings.metatexts import MetaTexts

from config.enums.users.roles import UserRolesEnum

from config.models.attributes import Attribute
from config.models.submissions.submissions import NewSubmission
from config.models.user import User
from config.models.submissions.metatexts import MetaTextSubmissionResponse
from config.models.submissions.submissions import SubmissionResponse, SubmissionIDResponse

from services.users import get_user_from_token
from services.submission import submission_to_json, check_for_missing_mandatory_attribute
from services.json import save_json
router = APIRouter(
    prefix="/api",
    tags=["Submission"],
    )


@router.get("/submission/id",
    summary = "Returns a unique id for a new submission.",
    response_model = SubmissionIDResponse)
def get_submission_id():
    """
    A unique id that cannot be changed for a project/data/submission.
    """
    return SubmissionIDResponse()

@router.post("/submission",summary="Add submission to the database")
def add_submission(submission : NewSubmission, user : User = Depends(get_user_from_token)):
    """
    Adds a submission to the database
    """
    ## move this out of the function - implement in db 
    db  = MCDatabase.getDatabase()
    attributes = db.attributes
    boolIdx = attributes["mandatory_for_submission"] == True
    print(attributes)
    print(attributes.columns.to_list())
    mandatory_attributes = [Attribute(**attr) for attr in attributes.loc[boolIdx,:].to_dict(orient="records")]
    missing_mand_attributes = check_for_missing_mandatory_attribute(submission, mandatory_attributes)
    print(missing_mand_attributes)
    json_data = submission_to_json (submission,user)
    save_json(json_data,"first_try.json")
    return "cool"


@router.get("/submission/submissions")
def get_submission(user : User = Depends(get_user_from_token)):
    """
    Returns the submissions depending on the user's role. 
    Curators and admins are able to see all submissions
    while standard users can only see their own submissions
    """
    db = MCDatabase.getDatabase()
    metadata = db.getJSONDatasets()
    if user.role < UserRolesEnum.CURATOR:
        return [dataset_meta for dataset_meta in metadata if dataset_meta.user_label == user.label] #check if in a list of collaborators ? 
    else:
        #return all if user at least curator
        return metadata 
    

@router.get("/submission/metatext",
            summary="Returns the metatext information that can be used to describe a submission.",
            response_model=MetaTextSubmissionResponse)
def get_meta_text(user : User = Depends(get_user_from_token)):
    """"""
    return MetaTexts().model_dump()

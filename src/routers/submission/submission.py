from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from typing import List, Annotated
from collections import OrderedDict

from lib.data.database.ABCDatabase import MCDatabase, MCAttributes
from lib.data.runs.runs import RunListCreator
from config.settings.general import get_general_settings
from config.settings.db import get_db_settings
from config.settings.metatexts import MetaTexts
from config.settings.email import get_email_settings
from config.enums.users.roles import UserRolesEnum
from config.enums.states import SubmissionStates

from config.exceptions.HTTPExceptions import mandatory_dataset_attrs_not_found_exception, label_not_found_exception, user_role_too_low

from config.models.attributes import AttributeModel
from config.models.submissions.submissions import NewSubmissionModel, UpdateDatasetAttributesInSubmission
from config.models.user import UserModel
from config.models.submissions.metatexts import MetaTextSubmissionResponse
from config.models.submissions.submissions import SubmissionIDResponse, DatasetSubmissionModel
from config.models.submissions.states import StateResponse, StateChangeModel
from config.models.submissions.timeline import TimeLineEntryModel, TimeLineModel
from config.models.submissions.runs import RunListModel, RunListRequestPropsModel, RunListResponseModel

from services.users import get_user_from_token, are_public_users_allowed, is_user_at_least_curator
from services.submission import submission_to_json, check_for_missing_mandatory_attribute
from services.json import save_json
from services.mail import send_email_in_background
from services.paths.utils import check_dir_exists, join_path






EMAIL_SETTINGS = get_email_settings()
GENERAL_SETTINGS = get_general_settings()
DB_SETTINGS = get_db_settings()

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

@router.get("/submissions/metatext",
            summary="Returns the metatext information that can be used to describe a submission.",
            response_model=MetaTextSubmissionResponse)
def get_meta_text(user : UserModel = Depends(get_user_from_token)):
    """"""
    print(MetaTexts().model_dump())
    return MetaTexts().model_dump()


@router.get("/submissions/states", summary="Returns the states enum as well as colors associated with the state.")
def get_project_states(user : UserModel = Depends(get_user_from_token)):
    """"""
    return StateResponse()


@router.post("/submissions",summary="Add submission to the database")
def add_submission(background_task : BackgroundTasks ,submission : NewSubmissionModel, user : UserModel = Depends(get_user_from_token)):
    """
    Adds a submission to the database
    """
    
    db  = MCDatabase.getDatabase()
    mandatory_attributes = db.getMandatorySubmissionAttributes()
    missing_mand_attributes = check_for_missing_mandatory_attribute(submission, mandatory_attributes)

    if len(missing_mand_attributes) > 0: return mandatory_dataset_attrs_not_found_exception.add_note(f"Missing : {[attr.tag for attr in missing_mand_attributes]}")
    json_data = submission_to_json(submission,user)
    
    data_dir = DB_SETTINGS.db_datadir
    dataset_dir = join_path(data_dir,submission.label)
    exists, dataset_dir = check_dir_exists(dataset_dir)
    if exists:
        params_path = join_path(dataset_dir,"params.json")
        #store json in resource
        save_json(DatasetSubmissionModel(**json_data).model_dump(exclude_none=True),params_path)
        #check if users are actually in DB and allowed
        #This information is not in the PublicUser and we need to get the user from the userDB
        check_collaborators = are_public_users_allowed(submission.collaborators)

        send_email_in_background(background_tasks=background_task,
                                subject=f"Submission Complete : {submission.title} ({submission.label})",
                                email_to=[user.email],
                                cc=[u.email for idx,u in enumerate(submission.collaborators) if check_collaborators[idx]],
                                body={
                                    "app_name" : GENERAL_SETTINGS.app_name,
                                    "first_name" : user.firstname,
                                    "title" : submission.title,
                                    "label" : submission.label
                                },
                                template_mame=EMAIL_SETTINGS.mail_submission_complete_template)
    


@router.patch("/submissions/{submission_label}/datasetattributes", summary = "Updates a submissions dataset attributes")
def update_submission(background_task : BackgroundTasks, 
                      submission_label : str,
                      state_change : StateChangeModel,  
                      datasetAttributes : UpdateDatasetAttributesInSubmission, 
                      user : UserModel = Depends(is_user_at_least_curator)) -> DatasetSubmissionModel:
    """
    Update datasetattribute along with the state if user is at least curator.
    Returns the updated version of the complete submission.

    TO DO: Add exception handling 
    """
    
    db = MCDatabase.getDatabase()
    if not db.doesLabelExists(submission_label): return label_not_found_exception
    # get submission from database 
    dataset = db.getDataset(submission_label)
    submission_state = state_change.state
    submissionMetaData = dataset.getMetaJson()
    # dump the model to a dict to modify it.
    metadata = submissionMetaData.model_dump()
    # update state using the State enumerater 
    metadata["state"] =  submission_state
    metadata["modified_on"] = datasetAttributes.modified_on 
    ## TODO : - mpve to service function
    time_line = metadata["timeline"].copy()
    updated_entries = time_line["entries"] + [TimeLineEntryModel(id=1,user_label=user.label,comment=state_change.comment,state=state_change.state).model_dump()]
    time_line["entries"] = updated_entries
    metadata["timeline"] = TimeLineModel(**time_line)

    # save dataset attributes 
    updated_dataset_attributes = OrderedDict([(attr.tag,[attrValue.tag for attrValue in datasetAttributes.datasetAttributeValues[attr.tag]]) 
                                      for attr in datasetAttributes.datasetAttributes if attr.tag in datasetAttributes.datasetAttributeValues])
    # pool dataset attributes
    metadata["dataset_attributes"] = {**metadata["dataset_attributes"], **updated_dataset_attributes}
    updated_submission = DatasetSubmissionModel(**metadata)
    #update meta data in dataset and write json file.
    
    dataset.write_json(updated_submission)

    send_email_in_background(background_tasks=background_task,
                             subject=f"Project {updated_submission.title} ({updated_submission.label}) state updated.",
                             email_to=[user.email],
                             include_setting_cc=True,
                             body={
                                 "app_name" : GENERAL_SETTINGS.app_name,
                                 "first_name" : user.firstname,
                                 "state" : SubmissionStates(updated_submission.state).name,
                                 "title" : updated_submission.title,
                                 "submission_label" : submission_label,
                                 "submission_url" : f"{GENERAL_SETTINGS.url}/dataset/{updated_submission.label}"
                             },
                             template_mame=EMAIL_SETTINGS.mail_project_state_template)

    return updated_submission    

@router.patch("/submissions/{label}/sampleattributes")
def update_sample_attributes(user : UserModel = Depends( is_user_at_least_curator)):
    pass 


@router.get("/submissions")
def get_submission(user : UserModel = Depends(get_user_from_token)):
    """
    Returns the submissions depending on the user's role. 
    Curators and admins are able to see all submissions
    while standard users can only see their own submissions
    """

    db = MCDatabase.getDatabase()
    metadata = db.getJSONDatasets()
    if user.role < UserRolesEnum.CURATOR:
        return [dataset_meta for dataset_label, dataset_meta in metadata.items() if dataset_meta.user_label == user.label] #check if in a list of collaborators ? 
    else:
        #return all if user at least curator
        return [dataset_meta for dataset_label, dataset_meta in metadata.items()]
    



@router.post("/submissions/{submission_label}/runlist", response_model=RunListResponseModel, tags = ["Runlist"])
def get_dataset_runlist(submission_label : str, runlist_props : RunListRequestPropsModel, user : UserModel = Depends(get_user_from_token)): #
    """
    Creates a runlist for a specific dataset. 
    A run is defined as the actual run and the number can be different from the number samples since
    an online and or offline fractionation might be used. In addition, samples might be pooled when
    using TMT or SILAC based quantification. 

    Updates the submission model runlist parameter. 

    Parameters
    ----------
    submission_label : str 
        The label assigned to the submission. 
    runlist_props : RunlistRequestPropsModel 
        The properties how to create the runlist 
    user : UserModel
        The user which is extracted from the token information. The user cannot be submitted as a user model but
        is based on FastAPI Depends function. 

    Returns
    -------


    Raises
    ------
    HTTPException
        If there is a value error when creating the runlist. Please see for more information in the
        RunListCreator's create function. 

    """
    db = MCDatabase.getDatabase()
    attributes = MCAttributes.getAttributeDatabase()
    attribute_values = attributes.getAttributeValues()
    attribute_value_by_tag = dict(zip(attribute_values["tag"],attribute_values["value"]))
    dataset = db.getDataset(label = submission_label)
    sample_idces, _ = dataset.getSamplesAttributes(map_tags_to=True,tag_mapper=attribute_value_by_tag)
    try:
        runlist = RunListCreator(sample_list=sample_idces, 
                                 user = user,
                                 dataset_label=submission_label, 
                                 **runlist_props.model_dump()
                                 ).create()
        meta_data = dataset.getMetaJson().model_dump()
        meta_data["runlist"] = runlist
        updated_meta_data = DatasetSubmissionModel(**meta_data)
        dataset.write_json(updated_meta_data,update=True)
        response = RunListResponseModel(**runlist.model_dump(), user_email=user.email, user_firstname=user.firstname, user_lastname=user.lastname)
        return response 
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    
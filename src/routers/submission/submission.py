import time 
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Query
from typing import List, Annotated, Literal, Dict
from collections import OrderedDict

import pandas as pd 

from lib.data.database.ABCDatabase import MCDatabase, MCAttributes, InvalidDatasetLabelError
from lib.data.runs.runs import RunListCreator
from lib.user.UserHandling import UserDB
from lib.data.database_helper.ABCDatabaseHelper import MCDatabaseHelper

from config.settings.general import get_general_settings
from config.settings.db import get_db_settings
from config.settings.metatexts import MetaTexts
from config.settings.email import get_email_settings
from config.enums.users.roles import UserRolesEnum
from config.enums.states import SubmissionStates

from config.exceptions.HTTPExceptions import mandatory_dataset_attrs_not_found_exception, label_not_found_exception, user_role_too_low, user_not_found, user_forbidden

from config.models.attributes import AttributeModel
from config.models.submissions.submissions import NewSubmissionModel, UpdateDatasetAttributesInSubmission, SubmissionQueryResponse
from config.models.user import UserModel, PublicUser
from config.models.submissions.metatexts import MetaTextSubmissionResponse
from config.models.submissions.submissions import SubmissionIDResponse, DatasetSubmissionModel, DatasetSubmissionResponseModel, SubmissionCountResponse
from config.models.submissions.states import StateResponse, StateChangeModel
from config.models.submissions.timeline import TimeLineEntryModel, TimeLineModel
from config.models.submissions.runs import RunListRequestPropsModel, RunListResponseModel

from services.users import get_user_from_token, are_public_users_allowed, is_user_at_least_curator, is_user_admin
from services.submission import submission_to_json, check_for_missing_mandatory_attribute, map_tags_to_attribute_in_metadata, get_dataset_from_database, add_timeline_entry_to_metadata
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


@router.patch("/submissions/{submission_label}/metatext", summary="Update the metatext of a submission.")
def post_meta_text(submission_label : str, metatext : Dict[str,str], user : UserModel = Depends(get_user_from_token)):
        
    db = MCDatabase.getDatabase()
    dataset = get_dataset_from_database(db,submission_label)
    metadata = dataset.getMetaJson()
    if user.role < UserRolesEnum.CURATOR and metadata.user_label != user.label:
        raise HTTPException(status_code=403,detail="Metatext can only be modified by the owner or a user that is at least curator.")
    metadata = metadata.model_dump()
    metadata["modified_on"] = time.time()
    metadata = add_timeline_entry_to_metadata(metadata, TimeLineEntryModel(id = 1, user_label=user.label, comment="Metatext updated.", state = metadata["state"]))
    metadata["metatext"] = metatext
    update_submission = DatasetSubmissionModel(**metadata)
    dataset.write_json(update_submission, update = True)
    return True 
    


@router.get("/submissions/metatext",
            summary="Returns the metatext information that can be used to describe a submission.",
            response_model=MetaTextSubmissionResponse)
def get_meta_text(user : UserModel = Depends(get_user_from_token)):
    """"""
    return MetaTexts().model_dump()


@router.get("/submissions/states", summary="Returns the states enum as well as colors associated with the state.")
def get_project_states(user : UserModel = Depends(get_user_from_token)):
    """"""
    return StateResponse()


@router.post("/submissions/{submission_label}/collaborators")
def add_collaborators(submission_label : str, collaborators : str, replace : bool = True, user : UserModel = Depends(get_user_from_token)):
    """_summary_

    Parameters
    ----------
    submission_label : str
        The submission label.
    collaborators : str
        user labels of collaborators, for multiple users separate them by a ';'
    replace : bool, optional
        If true, the existing collaborators are replaced, if false, the list is extended, by default True
    user : UserModel, optional
        _description_, by default Depends(get_user_from_token)

    Returns
    -------
    _type_
        _description_
    """
    db = MCDatabase.getDatabase()
    dataset = get_dataset_from_database(db,submission_label)
    metadata = dataset.getMetaJson().model_dump()
    query_collaborators = [ UserDB.get_user_by_label(user_label=coll_label) for coll_label in collaborators.split(";")]
    filtered_collaborators = [user for exists,user in query_collaborators if exists and user.allow_login]
    metadata["collaborators"] = filtered_collaborators
    return True


@router.get("/submissions/{submission_label}/owner", response_model=PublicUser)
def get_submission_owner(submission_label : str, user : UserModel = Depends(get_user_from_token)):
    """_summary_

    Parameters
    ----------
    submission_label : str
        The label of the submission the owner should be returned. 
    user : UserModel, optional
        _description_, by default Depends(get_user_from_token)

    Returns
    -------
    PublicUser
        Public user information.

    Raises
    ------
    label_not_found_exception
       The submission_label was not found.
    user_not_found
        If the user is not found in the database.
    """
    db = MCDatabase.getDatabase()
    dataset = get_dataset_from_database(db,submission_label)
    metadata = dataset.getMetaJson()
    user_label = metadata.user_label
    db_user = UserDB
    exists, user = db_user.get_user_by_label(user_label)
    if not exists:
        raise user_not_found
    return user
    

@router.post("/submissions/{submission_label}/owner")
def change_submission_owner(submission_label : str, 
                            user_label : str, 
                            add_prev_user_to_collaborators : bool = False, 
                            user : UserModel = Depends(is_user_admin)):
    """_summary_

    Parameters
    ----------
    submission_label : str
        The submission label
    user_label : str
       The user label that identifies the user. If the user_label does not exists, an user_not_found Exception is raise.
    add_prev_user_to_collaborators : bool, optional
        Query parameter that indicated, if the previous user should be added to the collaborators. by default False
    user : UserModel, optional
        The user model that is identified by the user. The minim state of the user must be ADMIN (4), by default Depends(is_user_admin)

    API Endpoint
    ------------
    POST /api/submissions/{submission_label}/owner.

    Returns
    -------
    bool
        Returns true if not errors occurred.

    Raises
    ------
    label_not_found_exception
        If the submission label does not exist.
    user_not_found
        If the user is not found in the database.
    user_forbidden
        If the user that is supposed to be the new owner is blocked (not allowed for login)
    """
    
    db = MCDatabase.getDatabase()
    dataset = get_dataset_from_database(db,submission_label)
    metadata = dataset.getMetaJson()
    
    db_user = UserDB
    exists, user = db_user.get_user_by_label(user_label)
    if not exists:
        raise user_not_found
    if not user.allow_login:
        raise user_forbidden
    metadata = metadata.model_dump()
    prev_user_label = metadata["user_label"]
    metadata["modified_on"] = time.time()
    metadata["user_label"] = user_label
    metadata["collaborators"] = [coll_label for coll_label in metadata["collaborators"] if coll_label != user_label]
    if add_prev_user_to_collaborators:
        metadata["collaborators"].append(prev_user_label)
    metadata = add_timeline_entry_to_metadata(metadata, TimeLineEntryModel(id = 1, user_label=user.label, comment="Project owner changed.", state = metadata["state"]))
    #  time_line = metadata["timeline"].copy()
    # updated_entries = time_line["entries"] + [TimeLineEntryModel(id=1,user_label=user.label,comment=state_change.comment,state=state_change.state).model_dump()]
    # time_line["entries"] = updated_entries
    # metadata["timeline"] = TimeLineModel(**time_line)
    
        
    update_submission = DatasetSubmissionModel(**metadata)
    dataset.write_json(update_submission, update = True)
    return True


@router.get("/submissions/count", response_model=Dict[str|int,SubmissionCountResponse])
def get_submissions_by_user_label(labels : str = None, group : Literal["state","user","attribute_tag","attribute_value_tag","feature","genotype"] = None, user : UserModel = Depends(get_user_from_token)):
    """Returns the the number submissions by a property. 


    Returns
    -------
    _type_
        _description_

    Raises
    ------
    """
    label_subset = None
    db_helper = MCDatabaseHelper.getDatabaseHelper()
    if labels is not None:
        label_subset = set(labels.split(";"))
    return db_helper.get_label_count_by(by=group, label_subset=label_subset)
    #if group is not in Literal => HTTPExcepction 


@router.get("/submissions/users", response_model=List)
def get_submissions_by_user_label(user : UserModel = Depends(get_user_from_token)):
    """Returns the the number and the labels by user that 
    are found in the database. 

    Returns
    -------
    _type_
        _description_

    Raises
    ------
    """
    db_helper = MCDatabaseHelper.getDatabaseHelper()
    return db_helper.get_labels_by_users()

@router.get("/submissions/q", response_model=SubmissionQueryResponse)
def get_submission_by_query(state : str|int = None,
                            query : Annotated[str | None, Query(min_length=1)] = None,
                            feature_key : str = None, 
                            attribute_value_tag : str = None, 
                            attribute_tag : str = None, 
                            genotype_label : str = None, 
                            user_label : str = None,
                            max_submissions : int = 50, 
                            join : Literal["inner","outer"] = "inner",
                            user : UserModel = Depends(get_user_from_token)
                            ): #user : UserModel = Depends(get_user_from_token)
    
    db_helper = MCDatabaseHelper.getDatabaseHelper()
    N = db_helper.get_metadata_count()
    db = MCDatabase.getDatabase()
    labels = []
    attribute_search_active = any(search_param is not None for search_param in [feature_key,attribute_tag,attribute_value_tag,genotype_label,state,user_label])
    attribute_search_labels = db_helper.get_labels(state=state,
                                                    feature_key=feature_key,
                                                    attribute_tag=attribute_tag,
                                                    attribute_value_tag=attribute_value_tag,
                                                    genotype_label=genotype_label,
                                                    user_label=user_label,
                                                    join=join
                                                    )
    if query is not None:
        labels_by_query = db_helper.get_labels_by_search_string(query, subset= attribute_search_labels if join == "inner" and attribute_search_active else None)
        if join == "inner":
            #the search happened already only in the subset of labels
            labels = labels_by_query
        else:
            labels  = labels_by_query + [label for label in attribute_search_labels if label not in labels_by_query]
    elif attribute_search_active:
        #if query is not defined, then the labels are simply the ones from the attribute_search
        labels = attribute_search_labels
    else:
        #otherwise get all 
        labels = db.getDataLabels()
        
    if attribute_search_active and len(labels) == 0: 
        #empty response
        return SubmissionQueryResponse(submissions=[],query_count=0,total_count=N,labels=[])
        
    metadata = list(db.getJSONDatasets(labels).values())
    #sort after creation date to show once that are required.
    metadata.sort(key = lambda x : x.created_on, reverse=True)
    query_match_count = len(metadata)
    if len(metadata) > max_submissions:
        metadata = metadata[:max_submissions]

    metadata = [map_tags_to_attribute_in_metadata(dataset_meta) for dataset_meta in metadata]
    
    return {
        "submissions" : metadata,
        "labels" : labels,
        "query_count"  : query_match_count,
        "total_count" : N
    }
    
    
    
@router.post("/submissions",summary="Add submission to the database")
def add_submission(background_task : BackgroundTasks ,submission : NewSubmissionModel, user : UserModel = Depends(get_user_from_token)):
    """
    Adds a submission to the database
    """
    
    db  = MCDatabase.getDatabase()
    
    if submission.label in db.getDataLabels():
        raise HTTPException(status_code=409, detail="Submission label exists already. Use the update function to update a submission.")
    
    mandatory_attributes = db.getMandatorySubmissionAttributes()
    missing_mand_attributes = check_for_missing_mandatory_attribute(submission, mandatory_attributes)

    if len(missing_mand_attributes) > 0: return mandatory_dataset_attrs_not_found_exception.add_note(f"Missing : {[attr.tag for attr in missing_mand_attributes]}")
    json_data = submission_to_json(submission,user)
   
    data_dir = DB_SETTINGS.db_datadir
    dataset_dir = join_path(data_dir,submission.label)
    exists, dataset_dir = check_dir_exists(dataset_dir)
    
        
    
    if exists:
        #params_path = join_path(dataset_dir,"params.json")
        #store json in resource
       # save_json(metadata.model_dump(exclude_none=True),params_path)
        
        #check if users are actually in DB and allowed
        #This information is not in the PublicUser and we need to get the user from the userDB
        if submission.includes_data:   
            json_data["state"] = SubmissionStates.DONE
        metadata = DatasetSubmissionModel(**json_data)
        datasetObj = db.getDatasetObject()(label = metadata.label) #initiate dataset 
        datasetObj._read_meta(meta = metadata)
        #save metadata first. TODO : Implement in insert? Or insert_metadata? 
        db.insert_meta(obj=datasetObj,meta=metadata)
        
        if submission.includes_data:    
            #TODO Check -> features (index to be in the annotation database with the selected database.?)
            sample_names = metadata.sample_names 
            datatable = pd.DataFrame(data = submission.data_array, columns=sample_names, index=submission.data_index)
            datatable = datatable.dropna(how="all")
            #no nan in index
            non_nan_index = datatable.index.dropna()
            datatable = datatable.loc[non_nan_index,:]
            #no duplicates in index 
            non_duplicates = datatable.index.duplicated(keep="first")
            datatable = datatable.loc[~non_duplicates,:]
           # datatable.to_csv(dataset_path, sep="\t")
           #TODO add filtering for features that are in the database? 
           #Lets discuss Andreas, as uniprot such as XADSD2-2 are somehow lost. 
            datasetObj._read_from_dataframe(datatable)
            db.insert(datasetObj)
            
        check_collaborators = are_public_users_allowed(submission.collaborators)
            
        send_email_in_background(background_tasks=background_task,
                                subject=f"Submission Complete : {submission.title} ({submission.label})",
                                email_to=[user.email],
                                cc=[u.email for idx,u in enumerate(submission.collaborators) if check_collaborators[idx]],
                                body={
                                    "app_name" : GENERAL_SETTINGS.app_name,
                                    "first_name" : user.firstname,
                                    "title" : submission.title,
                                    "label" : submission.label,
                                    "submission_url" : f"{GENERAL_SETTINGS.url}datasets/{submission.label}"
                                },
                                template_mame=EMAIL_SETTINGS.mail_submission_complete_template)

@router.patch("/submissions/{submission_label}/datasetattributes", summary = "Updates a submissions dataset attributes along with an optional change of state.")
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
    metadata = dataset.getMetaJson()
    submission_user_label = metadata.user_label 
    exists, submission_user = UserDB.get_user_by_label(user_label=submission_user_label)
    if not exists:
        raise HTTPException(status_code=404,details="The submission user label has not been found. Please change the owner of this submission first.")
    # dump the model to a dict to modify it.
    metadata = metadata.model_dump()
    # update state using the State enumerater 
    metadata["state"] =  submission_state
    metadata["modified_on"] = datasetAttributes.modified_on 
    
    ## TODO : - move to service function
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
    
    dataset.write_json(updated_submission, update = True)
    
    if state_change.prev_state != state_change.state:
        send_email_in_background(background_tasks=background_task,
                             subject=f"Project {updated_submission.title} ({updated_submission.label}) state updated.",
                             email_to=[submission_user.email, user.email],
                             include_setting_cc=True,
                             body={
                                 "app_name" : GENERAL_SETTINGS.app_name,
                                 "first_name" : submission_user.firstname,
                                 "state" : SubmissionStates(updated_submission.state).name,
                                 "title" : updated_submission.title,
                                 "submission_label" : submission_label,
                                 "submission_url" : f"{GENERAL_SETTINGS.url}datasets/{updated_submission.label}" #pydanitc HttpUrl (url) returns www.__.com/  
                             },
                             template_mame=EMAIL_SETTINGS.mail_project_state_template)

    return updated_submission    

@router.patch("/submissions/{label}/sampleattributes")
def update_sample_attributes(user : UserModel = Depends( is_user_at_least_curator)):
    pass 



@router.get("/submissions", response_model=List[DatasetSubmissionResponseModel])
def get_submission(labels : str = None, user : UserModel = Depends(get_user_from_token)):
    """
    Returns the submissions depending on the user's role. 
    Curators and admins are able to see all submissions
    while standard users can only see their own submissions
    """

    db = MCDatabase.getDatabase()
    metadata = db.getJSONDatasets()
    subset =  labels.split(";") if labels is not None else None
    #map_tags_to_attribute_in_metadata(list(metadata.values())[0])
    if user.role < UserRolesEnum.CURATOR:
        return [map_tags_to_attribute_in_metadata(dataset_meta) for dataset_label, dataset_meta in metadata.items() if dataset_meta.user_label == user.label and (subset is None or dataset_label in subset)] #check if in a list of collaborators ? 
    else:
        #return all if user at least curator
        return [map_tags_to_attribute_in_metadata(dataset_meta) for dataset_label, dataset_meta in metadata.items() if subset is None or dataset_label in subset]
    



@router.post("/submissions/{submission_label}/runlist", response_model=RunListResponseModel, tags = ["Runlist"])
def get_dataset_runlist(submission_label : str, runlist_props : RunListRequestPropsModel, user : UserModel = Depends(is_user_at_least_curator)): #
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
    RunListResponseModel


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
    dataset = get_dataset_from_database(db,submission_label)
    
    sample_idces, _ = dataset.getSamplesAttributes()
    
    if runlist_props.aggregate_on is not None and runlist_props.aggregate_on not in sample_idces.columns: raise HTTPException(status_code=400,detail="Aggregate on sample attribute tag not found.")
    #extract the value of the sample attributes which is used to label the runnames. 
    for columnName in sample_idces.columns:
        sample_idces[columnName] = ["_".join([attrValueTag.split(":")[-1] for attrValueTag in sample_attrs.split(" ")]) for sample_attrs in sample_idces[columnName].values]
    try:
        runlist = RunListCreator(sample_list=sample_idces, 
                                 user = user,
                                 dataset_label=submission_label, 
                                 **runlist_props.model_dump()
                                 ).create()
        meta_data = dataset.getMetaJson().model_dump()
        #overwrite the json runlist. 
        meta_data["runlist"] = runlist
        #TODO: add a timeline entry
        updated_meta_data = DatasetSubmissionModel(**meta_data)
        dataset.write_json(updated_meta_data,update=True)
        response = RunListResponseModel(**runlist.model_dump(), user_email=user.email, user_firstname=user.firstname, user_lastname=user.lastname)
        return response 
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    
    
    
@router.get("/submissions/{submission_label}/runlist", response_model=RunListResponseModel, tags = ["Runlist"])
def get_submission_runlist(submission_label : str, user : UserModel = Depends(get_user_from_token)) -> RunListResponseModel:
    db = MCDatabase.getDatabase()
    try: dataset = db.getDataset(label = submission_label) 
    except: raise label_not_found_exception
    metadata = dataset.getMetaJson()
    runlist = metadata.runlist
    if runlist is not None: 
        user_label = runlist.user_label 
        user_exists, user = UserDB.get_user_by_label(user_label)
        if user_exists:
            return RunListResponseModel(**metadata.runlist.model_dump(), user_email=user.email, user_firstname=user.firstname, user_lastname=user.lastname)
    raise HTTPException(status_code = 404, detail = "No runlist found.")
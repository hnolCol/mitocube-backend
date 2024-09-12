import time 
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Query
from typing import List, Annotated, Literal, Dict
from collections import OrderedDict
from neo4j.exceptions import ConstraintError
import pandas as pd 

from lib.data.database.ABCDatabase import MCDatabase, MCAttributes
from lib.data.runs.runs import RunListCreator
from lib.user.UserHandling import UserDB
from lib.data.database_helper.ABCDatabaseHelper import MCDatabaseHelper
from lib.data.database.Database import Database

from config.settings.general import get_general_settings
from config.settings.db import get_db_settings
from config.settings.metatexts import MetaTexts
from config.settings.email import get_email_settings
from config.enums.users.roles import UserRolesEnum
from config.enums.states import SubmissionStatesEnums
from config.models.parameter import APIParamString, APIParamInt
from config.models.searches import FulltextSearchResult
from config.models.news.news import NewsModel

from config.exceptions.HTTPExceptions import mandatory_dataset_attrs_not_found_exception, tag_not_found, user_role_too_low, user_not_found, user_forbidden

from config.models.attributes import AttributeModel
from config.models.submissions.submissions import NewSubmissionModel, UpdateDatasetAttributesInSubmission, SubmissionQueryResponse, DatasetAttributesResponse
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


DB = Database.DB()



EMAIL_SETTINGS = get_email_settings()
GENERAL_SETTINGS = get_general_settings()
DB_SETTINGS = get_db_settings()

router = APIRouter(
    prefix="/api",
    tags=["Submission"],
    )


@router.get("/submission/tag",
    summary = "Returns a unique tag for a new submission.",
    response_model = SubmissionIDResponse)
def get_submission_id(user : UserModel = Depends(get_user_from_token)):
    """
    A unique id that cannot be changed for a project/data/submission.
    TODO Check if its really unique ;) dummy func. 
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
    

@router.get("/submissions/{submission_tag}/metatext")
def get_metatext_by_tag(submission_tag : str, user : UserModel = Depends(get_user_from_token)):
    ""
    meta_text = DB.meta.get_metatext(tags = APIParamString(param=submission_tag).param)
    
    print(meta_text)
    return meta_text.to_dict(orient="records")

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


@router.get("/submissions/{submission_tag}/users")
def get_users_associated_with_submission(submission_tag : str, user : UserModel = Depends(get_user_from_token)) -> List[PublicUser]:
    """_summary_

    Parameters
    ----------
    submission_tag : str
        _description_
    user : UserModel, optional
        _description_, by default Depends(get_user_from_token)

    Returns
    -------
    List[PublicUser]
        _description_

    Raises
    ------
    user_not_found
        If the user is not found that is interpreted from the token. 
    tag_not_found
        
    """
    if not DB.submission_exists(tag = submission_tag): raise tag_not_found
    return DB.meta.get_users(dataset_tag=submission_tag)


@router.post("/submissions/{submission_tag}/collaborators")
def add_collaborators(submission_tag : str, collaborators : str, replace : bool = True, user : UserModel = Depends(get_user_from_token)):
    """_summary_

    Parameters
    ----------
    submission_tag : str
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
    dataset = get_dataset_from_database(db,submission_tag)
    metadata = dataset.getMetaJson().model_dump()
    query_collaborators = [ UserDB.get_user_by_label(user_label=coll_label) for coll_label in collaborators.split(";")]
    filtered_collaborators = [user for exists,user in query_collaborators if exists and user.allow_login]
    metadata["collaborators"] = filtered_collaborators
    return True


@router.get("/submissions/{submission_tag}/owner", response_model=PublicUser)
def get_submission_owner(submission_tag : str, user : UserModel = Depends(get_user_from_token)):
    """_summary_

    Parameters
    ----------
    submission_tag : str
        The label of the submission the owner should be returned. 
    user : UserModel, optional
        _description_, by default Depends(get_user_from_token)

    Returns
    -------
    PublicUser
        Public user information.

    Raises
    ------
    tag_not_found
       The submission_tag was not found.
    user_not_found
        If the user is not found in the database.
    """
    
    if not DB.submission_exists(tag = submission_tag): raise tag_not_found 
    user = DB.meta.get_owner(dataset_tag=submission_tag)
    return user 
    

@router.post("/submissions/{submission_tag}/owner")
def change_submission_owner(submission_tag : str, 
                            user_tag : str, 
                            add_prev_user_to_collaborators : bool = False, 
                            user : UserModel = Depends(is_user_admin)):
    """_summary_

    Parameters
    ----------
    submission_tag : str
        The submission tag
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
        Returns true if no errors occurred.

    Raises
    ------
    tag_not_found
        If the submission label does not exist.
    user_not_found
        If the user is not found in the database.
    user_forbidden
        If the user that is supposed to be the new owner is blocked (not allowed for login)
    """
    
    if not DB.users.exists(tag = user_tag): raise user_not_found 
    if not DB.submission_exists(tag = submission_tag): raise tag_not_found
    ok = DB.meta.update_owner(dataset_tag = submission_tag, user_tag = user_tag)
    if not ok:
        raise HTTPException(status_code=500,detail="There was an error when updating the owner.")
    return True


@router.get("/submissions/count", response_model=Dict[str|int,SubmissionCountResponse])
def get_submissions_by_user_label(tags : str = None, group : Literal["state","user","attribute","attribute_value","feature","genotype"] = None, user : UserModel = Depends(get_user_from_token)):
    """Returns the the number submissions by a property. 


    Returns
    -------
    _type_
        _description_

    Raises
    ------
    """
    
    counts = DB.submission_filter.get_counts(by = group, 
                                             tags = APIParamString(param=tags).param)
    return counts.to_dict(orient="index")
   

# @router.get("/submissions/users", response_model=List)
# def get_submissions_by_user_label(user : UserModel = Depends(get_user_from_token)):
#     """Returns the the number and the labels by user that 
#     are found in the database. 

#     Returns
#     -------
#     _type_
#         _description_

#     Raises
#     ------
#     """
#     db_helper = MCDatabaseHelper.getDatabaseHelper()
#     return db_helper.get_labels_by_users()


@router.get("/submission/ftquery")
def get_submission_by_fulltext(query : Annotated[str | None, Query(min_length=1)] = None, user : UserModel = Depends(get_user_from_token)):
    "Filters submisson by full text searches"
    matches : List[FulltextSearchResult] = DB.submission_filter.full_dataset_text_search(query)
    print(matches)



@router.get("/submissions/q", response_model=SubmissionQueryResponse)
def get_submission_by_query(state : str|int = None,
                            query : Annotated[str | None, Query(min_length=1)] = None,
                            feature_key : str = None, 
                            attribute_value_tag : str = None, 
                            attribute_tag : str = None, 
                            genotype_tag : str = None, 
                            user_tag : str = None,
                            max_submissions : int = 50, 
                            user : UserModel = Depends(get_user_from_token)
                            ): 
    """Counting the submissions based on various filter criteria. 

    Parameters
    ----------
    state : str | int, optional
        _description_, by default None
    query : Annotated[str  |  None, Query, optional
        _description_, by default 1)]=None
    feature_key : str, optional
        _description_, by default None
    attribute_value_tag : str, optional
        _description_, by default None
    attribute_tag : str, optional
        _description_, by default None
    genotype_tag : str, optional
        _description_, by default None
    user_tag : str, optional
        _description_, by default None
    max_submissions : int, optional
        _description_, by default 50
    user : UserModel, optional
        _description_, by default Depends(get_user_from_token)

    Returns
    -------
    SubmissionQueryResponse
        Summarizes the result with the following keys:
            - 'submission' (List[Dict]) : Minimal information about a submission.
            - 'tags' (List[str]) : List of submission tags 
            - 'query_count' : The number of submissions that match the filtering ignoring
            the provided limit.
            - 'total_count' (int) : The number of all submissions in the dataset. 
    """

    N = DB.submissions.count()
    tags = DB.submission_filter.get(
            state = APIParamInt(param = state).param, 
            attribute_tag=APIParamString(param=attribute_tag).param,
            attribute_value_tag=APIParamString(param=attribute_value_tag).param,
            protein_tag=APIParamString(param=feature_key).param,
            user_tag=APIParamString(param=user_tag).param,
            genotype_tag = APIParamString(param=genotype_tag).param,
            limit = max_submissions
            )
    if len(tags) == 0: 
        #empty response
        return SubmissionQueryResponse(submissions=[],query_count=0,total_count=N,tags=[])
    
    meta_data = DB.meta.get(tags = tags)
    
    d = {
        "submissions" : meta_data,
        "tags" : tags,
        "query_count"  : len(tags),
        "total_count" : N
    }
    return SubmissionQueryResponse(**d)
    
    
    
@router.post("/submissions", summary="Add submission to the database")
def add_submission(background_task : BackgroundTasks ,submission : NewSubmissionModel, user : UserModel = Depends(get_user_from_token)):
    """
    Adds a submission to the database
    """
    
    if DB.submission_exists(tag = submission.tag):
        raise HTTPException(status_code=409, detail="Submission label exists already. Use the update function to update the submission tag.")

    mandatory_attributes = DB.attributes.get_mandatory_attributes()
    missing_mand_attributes = check_for_missing_mandatory_attribute(submission, mandatory_attributes)
    if len(missing_mand_attributes) > 0:
        exception = mandatory_dataset_attrs_not_found_exception
        raise exception
    
    json_data = submission_to_json(submission,user)

    if submission.includes_data:   
        json_data["state"] = SubmissionStatesEnums.DONE
    metadata = DatasetSubmissionModel(**json_data)
    save_json(metadata.model_dump(),"MODEL.json")
    try:
        DB.insert_meta(meta_data=metadata)
    except ConstraintError:
        #should not happen, since it is controlled before, delete?
        raise HTTPException(status_code=409, detail="Submission tag exists already. Use the update function to update a submission.")
    except Exception as e:
        raise HTTPException(status_code=500, detail="An unknown error occured.")
    check_collaborators = are_public_users_allowed(submission.collaborators)
    if not submission.includes_data:
        DB.news.insert(NewsModel(user_tag=user.tag,
                             title="New Submission!",
                             content = f"New sample submission: {metadata.title} by {user.firstname}.", 
                             submission_tags=[metadata.tag])) 
    else:
         DB.news.insert(NewsModel(user_tag=user.tag,
                             title="New dataset!",
                             content = f"New dataset online: {metadata.title} by {user.firstname}.", 
                             submission_tags=[metadata.tag])) 
    
    send_email_in_background(background_tasks=background_task,
                        subject=f"Submission Complete : {submission.title} ({submission.tag})",
                        email_to=[user.email],
                        cc=[u.email for idx,u in enumerate(submission.collaborators) if check_collaborators[idx]],
                        body={
                            "app_name" : GENERAL_SETTINGS.app_name,
                            "first_name" : user.firstname,
                            "title" : submission.title,
                            "tag" : submission.tag,
                            "submission_url" : f"{GENERAL_SETTINGS.url}datasets/{submission.tag}"
                        },
                        template_mame=EMAIL_SETTINGS.mail_submission_complete_template)    

    return 

    
    
    
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
        #check for only nan columns 
        if datatable.dropna(axis=1, how='all').columns.size != datatable.columns.size:
            raise HTTPException(status_code=500,detail="A selected column contained only NaN. Please remove the column and submit the data again.")
        # datatable.to_csv(dataset_path, sep="\t")
        #TODO add filtering for features that are in the database? 
        #Lets discuss Andreas, as uniprot such as XADSD2-2 are somehow lost. 
        datasetObj._read_from_dataframe(datatable)
        db.insert(datasetObj)
        
    check_collaborators = are_public_users_allowed(submission.collaborators)
        
    
    
@router.get("/submissions/{submission_tag}/datasetattributes",summary="Returns the dataset attributes of a submission.")
def get_submission_attributes(submission_tag : str,
                              user : UserModel = Depends(get_user_from_token)) -> DatasetAttributesResponse:
    
    dataset_attribute_tags = DB.meta.get_dataset_attributes(tag = submission_tag)
    dataset_attribute_value_tags = [av_tag for av_tags in dataset_attribute_tags.values() for av_tag in av_tags]
    attributes = DB.attributes.get(tags = list(dataset_attribute_tags))
    values = DB.attributes.get_values(submission_tag=submission_tag, tags = dataset_attribute_value_tags)

    DatasetAttributesResponse(tag = submission_tag, attribute_values= values, attributes= attributes, tags = dataset_attribute_tags)
    return {'tags' : dataset_attribute_tags, 
            'attributes' : attributes, 
            'attribute_values' : values, 
            'tag' : submission_tag}

@router.patch("/submissions/{submission_tag}/datasetattributes", summary = "Updates a submissions dataset attributes along with an optional change of state.")
def update_submission(background_task : BackgroundTasks, 
                      submission_tag : str,
                      state_change : StateChangeModel,  
                      datasetAttributes : UpdateDatasetAttributesInSubmission, 
                      user : UserModel = Depends(is_user_at_least_curator)) -> bool:
    """
    Update datasetattribute along with the state if user is at least curator.
    Returns the updated version of the complete submission.

    TO DO: Add exception handling 
    """
    
    dataset_attributes = dict([(attribute_tag, [attribute_value.tag for attribute_value in attribute_values]) 
                          for attribute_tag, attribute_values in datasetAttributes.datasetAttributeValues.items() ])
    
    print(submission_tag)
    submission = {}
    
    ok = DB.meta.update_dataset_attributes(tag = submission_tag, dataset_attributes = dataset_attributes)
    
    print(ok)
    
    return ok 

    #notify the user if the state updated. For regular updates, no email is sent. 
    if state_change.prev_state != state_change.state:
        send_email_in_background(background_tasks=background_task,
                             subject=f"Project {submission.title} ({submission.tag}) state updated.",
                             email_to=[submission_user.email, user.email],
                             include_setting_cc=True,
                             body={
                                 "app_name" : GENERAL_SETTINGS.app_name,
                                 "first_name" : submission_user.firstname,
                                 "state" : SubmissionStatesEnums(updated_submission.state).name,
                                 "title" : submission.title,
                                 "submission_label" : submission_label,
                                 "submission_url" : f"{GENERAL_SETTINGS.url}datasets/{submission.tag}" #pydanitc HttpUrl (url) returns www.__.com/  
                             },
                             template_mame=EMAIL_SETTINGS.mail_project_state_template)
    print(datasetAttributes)
   # DB.meta.update_dataset_attributes(submisison_tag, )
    return 
    
    db = MCDatabase.getDatabase()
    if not db.doesLabelExists(submission_label): return tag_not_found
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
    except: raise tag_not_found
    metadata = dataset.getMetaJson()
    runlist = metadata.runlist
    if runlist is not None: 
        user_label = runlist.user_label 
        user_exists, user = UserDB.get_user_by_label(user_label)
        if user_exists:
            return RunListResponseModel(**metadata.runlist.model_dump(), user_email=user.email, user_firstname=user.firstname, user_lastname=user.lastname)
    raise HTTPException(status_code = 404, detail = "No runlist found.")
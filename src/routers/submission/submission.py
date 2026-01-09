
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Query
from typing import List, Annotated, Literal, Dict, Optional
from collections import OrderedDict
from neo4j.exceptions import ConstraintError
import pandas as pd 


from lib.data.runs.runs import RunListCreator


from lib.database.Database import Database

from config.settings.general import get_general_settings
from config.settings.db import get_db_settings
from config.settings.metatexts import MetaTexts
from config.settings.email import get_email_settings

from config.enums.states import SubmissionStatesEnums
from config.models.parameter import APIParamString, APIParamInt
from config.models.searches import FulltextSearchResult
from config.models.news.news import NewsModel

from config.exceptions.HTTPExceptions import tag_not_found, user_role_too_low, user_not_found, user_forbidden

from config.models.submissions.submissions import NewSubmissionModel, SubmissionQueryResponse, DatasetAttributesResponse
from config.models.user import UserModel, PublicUser
from config.models.submissions.metatexts import MetaTextSubmissionResponse
from config.models.submissions.submissions import SubmissionIDResponse, DatasetSubmissionModel, DatasetSubmissionResponseModel, SubmissionCountResponse
from config.models.submissions.states import StateChangeModel
from config.models.submissions.timeline import TimeLineEntryModel, TimeLineModel
from config.models.timeline import TimelineInputModel
from config.models.submissions.runs import RunListRequestPropsModel, RunListResponseModel
from config.enums.units import UnitsEnum


from services.users import get_user_from_token, is_user_at_least_curator, is_user_admin, is_creator_of_submission_or_curator


from services.mail import send_email_in_background

DB = Database.DB()

EMAIL_SETTINGS = get_email_settings()
GENERAL_SETTINGS = get_general_settings()
DB_SETTINGS = get_db_settings()

router = APIRouter(
    prefix="/api",
    tags=["Submission"],
    )


@router.get("/submissions/tag",
    summary = "Returns a unique tag for a new submission.",
    response_model = SubmissionIDResponse)
def get_submission_tag(user : UserModel = Depends(get_user_from_token)):
    """
    A unique id that cannot be changed for a project/data/submission.
    TODO Check if its really unique ;) dummy func. 
    """
    tag = DB.submissions.get_unique_tag()
    return SubmissionIDResponse(tag = tag)   


@router.get("/submissions/q")
def get_submission_by_query(state : str|int = None,
                            search_string : str = None,
                            feature_key : str = None, 
                            trait_tags : str = None, 
                            attribute_tag : str = None, 
                            genotype_tag : str = None, 
                            user_tags : str = None,
                            limit : int = 20, 
                            ordered : bool = True,
                            group_by_state : bool = True,
                            user : UserModel = Depends(get_user_from_token)
                            ) -> List[str]| Dict[str|int, List[str]]: 
    """Returns the submissions that match a given filter. 

    Parameters
    ----------
    state : str | int, optional
        _description_, by default None
    query : Annotated[str  |  None, Query, optional
        _description_, by default 1)]=None
    feature_key : str, optional
        _description_, by default None
    trait_tags : str, optional
        _description_, by default None
    attribute_tag : str, optional
        _description_, by default None
    genotype_tag : str, optional
        _description_, by default None
    user_tag : str, optional
        _description_, by default None
    limit : int, optional
        _description_, by default 50
    ordered : bool, optional
        _description_, by default True
    group_by_state : bool, optional
        groups the submission tags by state, by default True
    user : UserModel, optional
        _description_, by default Depends(get_user_from_token)

    Returns
    -------
    List of submission tags that match the filtering. 
    
    # SubmissionQueryResponse
    #     Summarizes the result with the following keys:
    #         - 'submission' (List[Dict]) : Minimal information about a submission.
    #         - 'tags' (List[str]) : List of submission tags 
    #         - 'query_count' : The number of submissions that match the filtering ignoring
    #         the provided limit.
    #         - 'total_count' (int) : The number of all submissions in the dataset. 
    """




    N = DB.submissions.count()
    tags = DB.submission_filter.find(
            search_string = search_string,
            state = APIParamInt(param = state).param, 
            attribute_tag=APIParamString(param=attribute_tag).param,
            trait_tags=APIParamString(param=trait_tags).param,
            protein_tag=APIParamString(param=feature_key).param,
            user_tags=APIParamString(param=user_tags).param,
            genotype_tag = APIParamString(param=genotype_tag).param,
            ordered = ordered,
            limit = limit
            )
    
    if group_by_state:
        #group by state
        tags = DB.submission_filter.group_by_state(tags = tags)
    return tags 
    


# @router.patch("/submissions/{submission_label}/metatext", summary="Update the metatext of a submission.")
# def post_meta_text(submission_label : str, metatext : Dict[str,str], user : UserModel = Depends(get_user_from_token)):
        
#     db = MCDatabase.getDatabase()
#     dataset = get_dataset_from_database(db,submission_label)
#     metadata = dataset.getMetaJson()
#     if user.role < UserRolesEnum.CURATOR and metadata.user_label != user.label:
#         raise HTTPException(status_code=403,detail="Metatext can only be modified by the owner or a user that is at least curator.")
#     #TO DO should be in the DEPENDS model 
#     metadata = metadata.model_dump()
#     metadata["modified_on"] = time.time()
#     metadata = add_timeline_entry_to_metadata(metadata, TimeLineEntryModel(id = 1, user_label=user.label, comment="Metatext updated.", state = metadata["state"]))
#     metadata["metatext"] = metatext
#     update_submission = DatasetSubmissionModel(**metadata)
#     dataset.write_json(update_submission, update = True)/s
#     return True 
    


@router.get("/submissions/{submission_tag}/exists")
def check_submission_exists(submission_tag: str) -> bool:
    "Checks if a submission exists by its tag."
    return DB.submissions.exists(tag=submission_tag)    


@router.get("/submissions/{submission_tag}/title")
def get_metatext_by_tag(submission_tag : str, user : UserModel = Depends(get_user_from_token)) -> str:
    "Returns the submission title by its tag."
    if not DB.submissions.exists(tag = submission_tag):
        return tag_not_found
    return DB.submissions.get_title(tag = submission_tag)

@router.get("/submissions/{submission_tag}/attributes")
def get_submission_attributes(submission_tag: str, user: UserModel = Depends(get_user_from_token)) -> List[str]:
    "Returns the submission attributes by its tag."
    if not DB.submissions.exists(tag = submission_tag):
        return tag_not_found
    return DB.submissions.get_attributes(tag = submission_tag)

@router.patch("/submissions/{submission_tag}/title")
def update_submission_title(submission_tag : str, title : str, user : UserModel = Depends(is_creator_of_submission_or_curator)) -> bool:
    "Updates the submission title by its tag."
    if not DB.submissions.exists(tag = submission_tag):
        return tag_not_found
    return DB.submissions.set_title(tag = submission_tag, title = title)

@router.get("/submissions/{submission_tag}/createdat")
def get_metatext_by_tag(submission_tag : str, user : UserModel = Depends(get_user_from_token)) -> float:
    "Returns the submission created at by its tag."
    if not DB.submissions.exists(tag = submission_tag):
        return tag_not_found
    return DB.submissions.get_created_at(tag = submission_tag)

@router.get("/submissions/{submission_tag}/metatext")
def get_metatext_by_tag(submission_tag : str, user : UserModel = Depends(get_user_from_token)) -> List[str]:
    "Returns the metatext tags associated with the given submission"
    return DB.metatexts.find(submission_tag = submission_tag)


@router.get("/submissions/{submission_tag}/metatext/{metatext_tag}")
def get_metatext_by_tag(submission_tag : str, metatext_tag : str, user : UserModel = Depends(get_user_from_token)):
    ""
    print(submission_tag,metatext_tag)
    meta_text = DB.meta.get_metatext(tags = APIParamString(param=submission_tag).param, metatext_tag = metatext_tag)
    if len(meta_text) == 0: raise HTTPException(status_code=404, detail="No meta text found.")
    return meta_text.to_dict(orient="records")[0]


@router.get("/submissions/metatext",
            summary="Returns the metatext information that can be used to describe a submission.",
            response_model=MetaTextSubmissionResponse)
def get_meta_text(user : UserModel = Depends(get_user_from_token)):
    """"""
    return MetaTexts().model_dump()


@router.get("/submissions/states", summary="Returns the states enum as well as colors associated with the state.")
def get_states(user : UserModel = Depends(get_user_from_token)):
    """"""
    return DB.submissions.get_states()


@router.get("/submissions/{submission_tag}/users")
def get_users_associated_with_submission(submission_tag : str, user : UserModel = Depends(get_user_from_token)) -> List[str]:
    """Returns all users that are associated with a submission. 

    Parameters
    ----------
    submission_tag : str
        The tag of the submission to get users for.
    user : UserModel, optional
        The user making the request, by default Depends(get_user_from_token)

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
    return DB.submissions.get_users(tag=submission_tag)


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


@router.get("/submissions/{submission_tag}/state", response_model=SubmissionStatesEnums)
def get_submission_owner(submission_tag : str, user : UserModel = Depends(get_user_from_token)):
    """Returns the state of a submission. 

    Parameters
    ----------
    submission_tag : str
        The tag of the submission the owner should be returned. 

    Returns
    -------
    SubmissionStatesEnums
        The state of the submission

    Raises
    ------
    tag_not_found
       The submission_tag was not found.
    """
    
    if not DB.submission_exists(tag = submission_tag): raise tag_not_found 
    return DB.submissions.get_state(tag = submission_tag)



@router.get("/submissions/{submission_tag}/views")
def get_submission_views(submission_tag : str, user : UserModel = Depends(get_user_from_token)):
    """Returns the view count of a submission.

    Parameters
    ----------
    submission_tag : str
        The tag of the submission the views should be returned.

    Returns
    -------
    int
        The view count of the submission.

    Raises
    ------
    tag_not_found
       The submission_tag was not found.
    """
    if not DB.submission_exists(tag = submission_tag): raise tag_not_found
    return DB.submissions.get_views(tag = submission_tag)


@router.post("/submissions/{submission_tag}/views")
def insert_submission_view(submission_tag : str, user : UserModel = Depends(get_user_from_token)):
    """Inserts a view for a submission.

    Parameters
    ----------
    submission_tag : str
        The tag of the submission to insert a view for.

    Returns
    -------
    bool
        Returns true if the view was successfully inserted.

    Raises
    ------
    tag_not_found
       The submission_tag was not found.
    """
    if not DB.submission_exists(tag = submission_tag): raise tag_not_found
    DB.submissions.insert_view(tag = submission_tag, user_tag = user.tag)
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


    
@router.post("/submissions", summary="Add submission to the database")
def add_submission(background_task : BackgroundTasks , submission : NewSubmissionModel, user : UserModel = Depends(get_user_from_token)):
    """
    Adds a submission to the database
    """    
    if DB.submission_exists(tag = submission.tag):
        raise HTTPException(status_code=409, detail="Submission tag exists already. Use the update function to update the submission or use a different tag (/api/submissions/tag).")


    print(submission, "submission worked")
    DB.submissions.insert(tag = submission.tag,
                          title = submission.title,
                          user_tag = user.tag,
                          collaborators = submission.collaborators)
    #set the state to submitted
    DB.submissions.set_state(tag = submission.tag, state = SubmissionStatesEnums.SUBMITTED, user_tag = user.tag) 
    DB.submissions.insert_attributes(tag = submission.tag, traits = submission.dataset_attributes) 
    #insert sampples and sample conditions (attributes/traits)
    for idx,sample_name in enumerate(submission.sample_names):
            sample_tag = DB.samples.insert(submission_tag = submission.tag, sample_name = sample_name, sample_index = idx)
            sample_attributes = submission.samples_attributes[idx] 
            DB.samples.insert_condition_application(sample_tag = sample_tag, sample_data = sample_attributes)
    ## add meta text 
    DB.submissions.insert_research_aim(tag = submission.tag, research_aim = submission.research_aim, user_tag = user.tag)

    return 
    


    # mandatory_attributes = DB.attributes.get_mandatory_attributes()
    # missing_mand_attributes = check_for_missing_mandatory_attribute(submission, mandatory_attributes)
    
    # if len(missing_mand_attributes) > 0:
    #     exception = mandatory_dataset_attrs_not_found_exception
    #     raise exception

    
    # metadata = DatasetSubmissionModel(
    #     created_on=submission.created_on,
    #     title=submission.title,
    #     tag= submission.tag,
    #     replicates=submission.replicates,
    #     n_samples=len(submission.sampleNames),
    #     user_tag=user.tag, 
    #     collaborators=submission.collaborators,
    #     state = SubmissionStatesEnums.DONE if submission.includes_data else SubmissionStatesEnums.SUBMITTED,
    #     sample_names=submission.sampleNames,
    #     dataset_attributes=submission.datasetAttributes,
    #     samples_attributes=submission.samplesAttributes,
    #     samples_genotypes=submission.genotypes,
    #     dataset_attribute_input=submission.datasetAttributeInput,
    #     metatext=submission.metatext
    # )

    
    # #save_json(metadata.model_dump(),"MODEL.json")
    # try:
    #     DB.insert_meta(meta_data=metadata)
    # except ConstraintError:
    #     #should not happen, since it is controlled before, delete?
    #     raise HTTPException(status_code=409, detail="Submission tag exists already. Use the update function to update a submission.")
    # except Exception as e:
    #     print(e)
    #     raise HTTPException(status_code=500, detail="An unknown error occured.")
    # check_collaborators = are_public_users_allowed(user_tags=metadata.collaborators)
    
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
                        template_name=EMAIL_SETTINGS.mail_submission_complete_template)    

    return 
    
    
@router.get("/submissions/{submission_tag}/datasetattributes",summary="Returns the dataset attributes of a submission.")
def get_submission_attributes(submission_tag : str,
                              user : UserModel = Depends(get_user_from_token)) -> DatasetAttributesResponse:
    
    dataset_attribute_tags = DB.meta.get_dataset_attributes(tag = submission_tag)

    return {'tags' : dataset_attribute_tags, 
            'tag' : submission_tag,
            }

@router.patch("/submissions/{submission_tag}/state/{state_tag}")
def update_submission_state(background_task : BackgroundTasks, 
                          submission_tag : str, 
                          state_tag : SubmissionStatesEnums, 
                          user : UserModel = Depends(is_user_at_least_curator)) -> bool:
    """
    Updates the state of a submission. The user must be at least curator to update the state.
    Returns the updated version of the complete submission.
    
    Parameters
    ----------
    background_task : BackgroundTasks
        Background task to send an email in the background.
    state_tag : SubmissionStatesEnums
        The new state to set.
    submission_tag : str
        The tag of the submission to update.
    user : UserModel, optional
        The user making the request, by default Depends(is_user_at_least_curator)

    Returns
    -------
    bool
        True if the state was updated successfully.
    
    Raises
    ------
    HTTPException
        If the submission with the given tag does not exist or if there is an error during the update.
    """
    
    if not DB.submissions.exists(tag = submission_tag): raise tag_not_found
  
    ok = DB.submissions.update_state(tag = submission_tag, new_state = state_tag, user_tag = user.tag)

    if ok:
        submission_title = DB.submissions.get_title(tag = submission_tag) # to check if the submission exists and to get the title
        submission_user_tags = DB.submissions.get_users(tag = submission_tag)
        print(submission_user_tags,"tags")
        submission_users = [DB.users.get_user_by_tag(tag = user_tag) for user_tag in submission_user_tags if DB.users.exists(tag = user_tag)]
        
        print(submission_users)
        
        if len(submission_users) == 0:
            raise HTTPException(status_code=404, detail="Submission user not found. The state of the submission has been updated, but the user could not be found.")
        user_emails = [user.email] + [user.email for user in submission_users]
        first_names = [user.firstname for user in submission_users]
        
        send_email_in_background(background_tasks=background_task,
                             subject=f"Project {submission_title} ({submission_tag}) state updated.",
                             email_to=user_emails,
                             include_setting_cc=True,
                             body={
                                 "app_name" : GENERAL_SETTINGS.app_name,
                                 "first_name" : ", ".join(first_names),
                                 "state" : SubmissionStatesEnums(state_tag).name,
                                 "title" : submission_title,
                                 "submission_label" : submission_tag,
                                 "submission_url" : f"{GENERAL_SETTINGS.url}datasets/{submission_tag}" #pydanitc HttpUrl (url) returns www.__.com/  
                             },
                             template_name=EMAIL_SETTINGS.mail_project_state_template)
    return ok 

@router.patch("/submissions/{submission_tag}/datasetattributes", summary = "Updates a submissions dataset attributes along with an optional change of state.")
def update_submission(background_task : BackgroundTasks, 
                      submission_tag : str,
                      state : SubmissionStatesEnums, 
                      state_change : StateChangeModel,  
                      dataset_attributes : Dict[str,List[str]], # attribute_tag, List[trait_tag] 
                      dataset_attribute_input : Optional[Dict[str,Dict[str,Dict]]] = None,
                      user : UserModel = Depends(is_user_at_least_curator)) -> bool:
    """
    Update datas etattribute along with the state if user is at least curator.
    Returns the updated version of the complete submission.

    TO DO: Add exception handling 
    """
    
    # dataset_attributes = dict([(attribute_tag, [attribute_value.tag for attribute_value in attribute_values]) 
    #                       for attribute_tag, attribute_values in datasetAttributes.datasetAttributeValues.items() ])  
    try:  
        if not DB.submissions.exists(tag = submission_tag): return tag_not_found
        
        ok = DB.submissions.update_state(tag = submission_tag, new_state = state_change.state, user_tag = user.tag)
        if ok:
            dataset_update_stats = DB.meta.update_dataset_attributes(tag = submission_tag, dataset_attributes = dataset_attributes, dataset_attribute_input = dataset_attribute_input)       
        
            DB.timeline.insert(TimelineInputModel(content=f"Dataset attributes have been updated by {user.firstname}. {dataset_update_stats['number_deleted_traits']} traits were removed. ({', '.join(dataset_update_stats['deleted_trait_tags'])}). {dataset_update_stats['number_added_traits']} traits were added. ({', '.join(dataset_update_stats['added_trait_tags'])}).", 
                                            submission_tag=submission_tag, 
                                            submission_state=state_change.state,
                                            user_tag=user.tag))
    except Exception as e :
        raise HTTPException(status_code=400, detail=str(e))
    return True



@router.get("/submissions/{submission_tag}/sampleattributes")
def get_sample_attributes(submission_tag : str, user : UserModel = Depends(get_user_from_token)):
    
    sample_attrs, sample_map = DB.meta.get_sample_attributes_and_genotypes(tag = submission_tag) #: Dict[str,Dict[str,List[int]]], pd.DatafRmae
    
    return {"sample_attributes" : sample_attrs, "sample_map" : sample_map }


@router.get("/submissions/{submission_tag}/summary")
def get_submission_summary_string(submission_tag : str, user : UserModel = Depends(get_user_from_token)) -> str:
    "Returns a string with dataset and sample attributes"
    summary_strings = DB.submission_summary.get(submission_tag)
    
    return "\n".join(summary_strings)

@router.get("/submissions/{submission_tag}/samples")
def get_submission_samples(submission_tag : str, user : UserModel = Depends(get_user_from_token)) -> List[str]:
    "Returns the samples tags associated with the submission"
    return DB.submissions.get_samples(tag=submission_tag)

@router.get("/submissions/{submission_tag}/samplelist")
def get_sample_list_as_tsv(submission_tag : str, user : UserModel = Depends(get_user_from_token)) -> str:
    samples = DB.submissions.get_sample_list(tag=submission_tag)
    samples_string = pd.DataFrame.from_dict(samples).sort_values(by="index")
    return samples_string.to_csv(sep="\t", index = None)


@router.get("/submissions", response_model=List[DatasetSubmissionResponseModel])
def get_submission(labels : str = None, user : UserModel = Depends(get_user_from_token)):
    """
    Returns the submissions depending on the user's role. 
    Curators and admins are able to see all submissions
    while standard users can only see their own submissions
    """

    # db = MCDatabase.getDatabase()
    # metadata = db.getJSONDatasets()
    # subset =  labels.split(";") if labels is not None else None
    # #map_tags_to_attribute_in_metadata(list(metadata.values())[0])
    # if user.role < UserRolesEnum.CURATOR:
    #     return [map_tags_to_attribute_in_metadata(dataset_meta) for dataset_label, dataset_meta in metadata.items() if dataset_meta.user_label == user.label and (subset is None or dataset_label in subset)] #check if in a list of collaborators ? 
    # else:
    #     #return all if user at least curator
    #     return [map_tags_to_attribute_in_metadata(dataset_meta) for dataset_label, dataset_meta in metadata.items() if subset is None or dataset_label in subset]
    



@router.post("/submissions/{submission_tag}/runlist", response_model=RunListResponseModel, tags = ["Runlist"])
def get_dataset_runlist(submission_tag : str, runlist_props : RunListRequestPropsModel, user : UserModel = Depends(is_user_at_least_curator)): #
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
    # db = MCDatabase.getDatabase()
    # attributes = MCAttributes.getAttributeDatabase()
    # attribute_values = attributes.getAttributeValues()
    # attribute_value_by_tag = dict(zip(attribute_values["tag"],attribute_values["value"]))
    # dataset = get_dataset_from_database(db,submission_label)
    
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
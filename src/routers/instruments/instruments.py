from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from typing import List
from lib.data.database.ABCDatabase import MCAttributes
from services.users import is_user_admin, get_user_from_token

from lib.data.database_helper.ABCDatabaseHelper import MCDatabaseHelper

from config.models.user import UserModel
from config.models.attributes import AttributeValueModel
from config.enums.states import SubmissionStates
from lib.user.UserHandling import UserDB

import numpy as np 
router = APIRouter(
    prefix="/api/instruments",
    tags=["Remote Control"]
    )


@router.get("", response_model=List[AttributeValueModel])
def get_instruments(user : UserModel = Depends(get_user_from_token)):
    """Returns all the instruments as an attribute value model that 
    were used in the database and are annotated in one or more submissions. 
    Hence it is different from get all attribute values for the attribute tag
    that defines the instruments. 

    API Endpoint
    ------------
    GET /api/instruments/

    Returns
    -------
    List[AttributeValueModel]
        The list of instruments.
    """
    db_helper = MCDatabaseHelper.getDatabaseHelper()
    db_attributes = MCAttributes.getAttributeDatabase()
    instrument_values = db_attributes.getAttributeValues(tags=list(db_helper.get_instruments()))
    return instrument_values.to_dict(orient="records")
    
    
    
    
@router.get("/{instrument_tag}/stats")
def get_instrument_by_tag(instrument_tag : str, user : UserModel = Depends(get_user_from_token)):
    ""
    db_helper = MCDatabaseHelper.getDatabaseHelper()
    instruments = db_helper.get_instruments()
    if instrument_tag not in instruments: raise HTTPException(status_code=404,detail="The instrument was not found.")
    sample_numbers_per_instrument = db_helper.get_sample_number_by_instrument()
    number_samples_per_project = np.array(sample_numbers_per_instrument[instrument_tag])
    #get datasets measured on that instrument
    instrument_dataset_labels = db_helper.get_labels_by_attribute_value_tag(instrument_tag)
    submissions = db_helper.get_labels_by_instrument(instrument_tag)
    for submission in submissions:
        exists, user = UserDB.get_user_by_label(submission["user_label"])
        if exists:
            submission["user"] = user
        
    states_for_instrument_labels = db_helper.get_label_count_by_state(label_subset=instrument_dataset_labels)
    is_measuring = SubmissionStates.MEASURING in states_for_instrument_labels
    if is_measuring:
        #there should be only one measuring. 
        is_measuring_label = list(states_for_instrument_labels[SubmissionStates.MEASURING]["submission_labels"])[0]
        measuring_submission = [submission for submission in submissions if submission["label"] == is_measuring_label][0]
    #get the total number of datasets that have an instrument annotation
    #calculate the fraction that the instrument measured.
    total_dataset_labels_with_instrument = db_helper.get_labels_by_attribute_tag(db_helper._instrument_attribute_tag)

    first_use = db_helper.get_instrument_first_use(instrument_tag)
    
   
    published_datasets_found = SubmissionStates.PUBLISHED in states_for_instrument_labels
    
    return {
        "is_measuring" : is_measuring,
        "is_measuring_submission" : measuring_submission,
        "number_samples" : np.mean(number_samples_per_project), 
        "first_use" : first_use,
        "submissions" : submissions,
        "number_datasets" : len(instrument_dataset_labels), 
        "number_datasets_published" : 0 if not published_datasets_found else states_for_instrument_labels[SubmissionStates.PUBLISHED]["submission_count"],
        "relative_number_datasets" : len(instrument_dataset_labels)/len(total_dataset_labels_with_instrument)}

    
    
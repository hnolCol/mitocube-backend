from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from typing import List
from lib.database.ABCDatabase import MCAttributes
from services.users import is_user_admin, get_user_from_token

from lib.data.database_helper.ABCDatabaseHelper import MCDatabaseHelper

from config.models.user import UserModel
from config.models.attributes import AttributeValueModel, TraitModel
from config.enums.states import SubmissionStatesEnums
from lib.user.UserHandling import UserDB

from lib.database.Database import Database

import numpy as np 
router = APIRouter(
    prefix="/api/instruments",
    tags=["Remote Control"]
    )

DB = Database.DB()

@router.get("")
def get_instruments(type : str = None, user : UserModel = Depends(get_user_from_token)):
    ""
    return DB.instruments.get(instrument_type = type)
    

@router.get("/types")
def get_instrument_type_tags(user : UserModel = Depends(get_user_from_token)) -> List[str]:
    "Instruments are grouped by type."
    return DB.instruments.get_types()


@router.get("/{instrument_tag}")
def get_instrument_by_tag(instrument_tag : str, user : UserModel = Depends(get_user_from_token)) -> TraitModel:
    "Since instruments are also traits in the database, we can use the attributes route."
    if not DB.attributes.exists(trait = instrument_tag): raise HTTPException(status_code=404, detail="Instrument not found.")
    instrument = DB.attributes.trait(trait_tag = instrument_tag)
    return instrument

@router.get("/{instrument_tag}/projects/count")
def get_instrument_by_tag(instrument_tag : str, user : UserModel = Depends(get_user_from_token)):
    "Return the number of projects the instrument was used in."
    return 9 

@router.get("/{instrument_tag}/samples/count")
def get_instrument_by_tag(instrument_tag : str, user : UserModel = Depends(get_user_from_token)):
    "Return the number of samples the instrument measured."
    return 12 



    
@router.get("/{instrument_tag}/stats")
def get_instrument_by_tag(instrument_tag : str, user : UserModel = Depends(get_user_from_token)):
    ""

    
    measuring_submission = {}
    db_helper = MCDatabaseHelper.getDatabaseHelper()
    instruments = db_helper.get_instruments()
    if instrument_tag not in instruments: raise HTTPException(status_code=404,detail="The instrument was not found.")
    sample_numbers_per_instrument = db_helper.get_sample_number_by_instrument()
    number_samples_per_project = np.array(sample_numbers_per_instrument[instrument_tag])
    #get datasets measured on that instrument
    instrument_dataset_labels = db_helper.get_labels_by_attribute_value_tag(instrument_tag)
    submissions = db_helper.get_labels_by_instrument(instrument_tag)
    for submission in submissions:
        exists, user = UserDB.get_user_by_label(submission["user_tag"])
        if exists:
            submission["user"] = user
        
    states_for_instrument_labels = db_helper.get_label_count_by_state(label_subset=instrument_dataset_labels)
    is_measuring = SubmissionStatesEnums.MEASURING in states_for_instrument_labels
    if is_measuring:
        #there should be only one measuring. 
        is_measuring_label = list(states_for_instrument_labels[SubmissionStatesEnums.MEASURING]["submission_labels"])[0]
        measuring_submission = [submission for submission in submissions if submission["label"] == is_measuring_label][0]
    #get the total number of datasets that have an instrument annotation
    #calculate the fraction that the instrument measured.
    total_dataset_labels_with_instrument = db_helper.get_labels_by_attribute_tag(db_helper._instrument_attribute_tag)

    first_use = db_helper.get_instrument_first_use(instrument_tag)
    
   
    published_datasets_found = SubmissionStatesEnums.ACTIVE in states_for_instrument_labels
    
    return {
        "is_measuring" : is_measuring,
        "is_measuring_submission" : measuring_submission,
        "number_samples" : np.mean(number_samples_per_project), 
        "first_use" : first_use,
        "submissions" : submissions,
        "number_datasets" : len(instrument_dataset_labels), 
        "number_datasets_published" : 0 if not published_datasets_found else states_for_instrument_labels[SubmissionStatesEnums.ACTIVE]["submission_count"],
        "relative_number_datasets" : len(instrument_dataset_labels)/len(total_dataset_labels_with_instrument)}

    
    
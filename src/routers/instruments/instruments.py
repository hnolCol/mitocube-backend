from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from typing import List
from services.users import is_user_admin, get_user_from_token, is_user_at_least_curator
from lib.database.Database import get_db



from config.models.user import UserModel
from config.models.attributes import AttributeValueModel, TraitModel
from config.enums.states import SubmissionStatesEnums
from config.enums.users.roles import UserRolesEnum
from config.models.permissions import PermissionResponseModel

from config.models.instruments import InstrumentStateModel, InstrumentStateHistoryResponseModel, InstrumentsStateResponseModel


from lib.database.abstract.Database import DatabaseABC

import numpy as np 
router = APIRouter(dependencies=[Depends(get_user_from_token)],
    prefix="/api/instruments",
    tags=["Remote Control"]
    )


@router.get("/types")
def get_instrument_type_tags(user: UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> List[dict]:
    """Instruments are grouped by type."""
    return db.instruments.get_types()

@router.get("")
def get_instruments(type: str = None, user: UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> List[dict]:
    """Get instruments with their display text, optionally filtered by type"""
    return db.instruments.get(instrument_type=type)

@router.get("/permissions") 
def get_instrument_permissions(user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> PermissionResponseModel:
    "Returns the instrument tags the user has permission to access."
    return PermissionResponseModel(user_tag=user.tag, create= user.role >= UserRolesEnum.CURATOR, archive= user.role >= UserRolesEnum.CURATOR, comment = user.role >= UserRolesEnum.STANDARD, edit= user.role >= UserRolesEnum.CURATOR) 

@router.get("/overview")
def get_instruments_overview(user: UserModel = Depends(get_user_from_token)) -> List[dict]:
    "Per-instrument current state and sample count, via the runlist path."
    return DB.instruments.get_overview()

@router.get("/states/all")
def get_all_instrument_states(user: UserModel = Depends(get_user_from_token)) -> List[InstrumentStateModel]:
    return DB.instrument_states.get_all()


@router.get("/states/q")
def get_instrument_state_by_search_string(search_string : str, limit : int = 20, db : DatabaseABC = Depends(get_db)):
    return db.instrument_states.find(search_string)


@router.get("/states/{state_tag}")
def get_instrument_state_by_tag(state_tag : str, db : DatabaseABC = Depends(get_db)) -> InstrumentStateModel:
    return db.instrument_states.get(tag = state_tag)


@router.get("/{instrument_tag}")
def get_instrument_by_tag(instrument_tag : str, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> TraitModel:
    "Since instruments are also traits in the database, we can use the attributes route."
    if not db.attributes.exists(trait = instrument_tag): raise HTTPException(status_code=404, detail="Instrument not found.")
    instrument = db.attributes.trait(trait_tag = instrument_tag)
    return instrument

@router.get("/{instrument_tag}/states")
def get_instrument_state(instrument_tag : str, limit : int = 1, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> List[str]:
    "Returns the states of an instrument. The states are always ordered by the creation time, with the most recent state first."
    if not db.attributes.exists(trait = instrument_tag): raise HTTPException(status_code=404, detail="Instrument not found.")
    return db.instrument_states.get_instrument_state(instrument_tag = instrument_tag , limit = limit)

RUNNING_INSTRUMENT_STATE = "state.instrument.running"
@router.post("/{instrument_tag}/states/{state_tag}")
def set_instrument_state(instrument_tag : str, state_tag : str, user : UserModel = Depends(is_user_at_least_curator), db : DatabaseABC = Depends(get_db)) -> dict:
    "Sets the state of an instrument. The state is added to the history of the instrument. The state is not overwritten, but added as a new entry in the history. The duration of the previous state is calculated and stored in the database."
    if not db.attributes.exists(trait = instrument_tag): raise HTTPException(status_code=404, detail="Instrument not found.")
    if not db.instrument_states.exists(tag = state_tag): raise HTTPException(status_code=404, detail="State not found.")
    db.instrument_states.set_state(tag = state_tag, instrument_tag = instrument_tag)
    paused = db.instruments.pause_measuring_submissions(instrument_tag) if state_tag != RUNNING_INSTRUMENT_STATE else []
    return {"paused_submissions": paused}

@router.get("/{instrument_tag}/states/durations") 
def get_instrument_state_durations(instrument_tag : str, timestamp_min : float = None, timestamp_max : float = None, limit : int = None, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> List[InstrumentStateHistoryResponseModel]:
    "Returns the duration of all states for an instrument." 
    return db.instrument_states.get_state_durations(instrument_tag = instrument_tag, timestamp_min = timestamp_min, timestamp_max = timestamp_max, limit = limit)


@router.get("/{instrument_tag}/states/durations/fraction")
def get_fractional_instrument_state_durations(instrument_tag : str, timestamp_min : float = None, timestamp_max : float = None, limit : int = None, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> List[dict]:
    fractions = db.instrument_states.get_fractional_state_durations(instrument_tag=instrument_tag, timestamp_min = timestamp_min, timestamp_max = timestamp_max, limit = limit)
    return fractions.to_dict(orient="records")

@router.get("/{instrument_tag}/states") 
def get_instrument_states(instrument_tag : str, limit : int = None, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> List[InstrumentsStateResponseModel]:
    "Returns the state tags for an instrument." 
    return db.instrument_states.get_instrument_state(instrument_tag = instrument_tag, limit = limit)
    
    #return db.instrument_states.get_states(instrument_tag = instrument_tag, timestamp_min = timestamp_min, timestamp_max = timestamp_max, limit = limit)


@router.get("/{instrument_tag}/states/{state_tag}/durations") 
def get_instrument_specific_state_durations(instrument_tag : str, state_tag : str, timestamp_min : float = None, timestamp_max : float = None, limit : int = None, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> List[InstrumentStateHistoryResponseModel]:
    "Returns the duration of a specific state for an instrument." 
    return db.instrument_states.get_state_durations(instrument_tag = instrument_tag, state_tag = state_tag, timestamp_min = timestamp_min, timestamp_max = timestamp_max, limit = limit)


@router.get("/{instrument_tag}/projects/count")
def get_instrument_by_tag(instrument_tag : str, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)):
    "Return the number of projects the instrument was used in."
    return 9 

@router.get("/{instrument_tag}/samples/count")
def get_instrument_by_tag(instrument_tag : str, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)):
    "Return the number of samples the instrument measured."
    return db.samples.count(instrument_tag = instrument_tag)
    return 12 #db.samples.count(instrument_tag = instrument_tag)

@router.get("/{instrument_tag}/quantification/summary")
def get_instrument_quantification_summary(
    instrument_tag: str,
    timestamp_min: float = None,
    timestamp_max: float = None,
    user: UserModel = Depends(get_user_from_token),
) -> List[dict]:
    return DB.instruments.get_quantification_summary_by_month(
        instrument_tag=instrument_tag, timestamp_min=timestamp_min, timestamp_max=timestamp_max
    )

@router.get("/{instrument_tag}/state/durations/summary")
def get_instrument_state_duration_summary(
    instrument_tag: str,
    timestamp_min: float = None,
    timestamp_max: float = None,
    user: UserModel = Depends(get_user_from_token),
) -> List[dict]:
    return DB.instrument_states.get_state_duration_summary(
        instrument_tag=instrument_tag, timestamp_min=timestamp_min, timestamp_max=timestamp_max
    )

    
@router.get("/{instrument_tag}/stats")
def get_instrument_by_tag(instrument_tag : str, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)):
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

    
@router.get("/{instrument_tag}/submissions/past")
def get_instrument_past_submissions(
    instrument_tag: str,
    offset: int = 0,
    limit: int = 20,
    user: UserModel = Depends(get_user_from_token),
) -> dict:
    return DB.instruments.get_past_submissions_paginated(instrument_tag=instrument_tag, offset=offset, limit=limit)


@router.get("/{instrument_tag}/quantification/unique-count")
def get_instrument_unique_protein_group_count(
    instrument_tag: str,
    year: int,
    user: UserModel = Depends(get_user_from_token),
) -> int:
    return DB.instruments.get_unique_protein_group_count_by_year(instrument_tag=instrument_tag, year=year)
from typing import List 

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException

from lib.database.Database import Database

from config.models.user import UserModel
from config.models.maintenance import MaintenanceEventInsertModel
from services.users import is_user_admin, get_user_from_token, is_user_at_least_curator


DB = Database.DB()

router = APIRouter(
    prefix="/api/maintenance",
    tags=["Maintenance", "Performance"]
    )


@router.post("/" )
def insert_maintenance(maintenance_event: MaintenanceEventInsertModel, user: UserModel = Depends(is_user_at_least_curator)):
    maintenance_event = MaintenanceEventInsertModel(**maintenance_event.model_dump(exclude=["user_tag"]), user_tag=user.tag)
    DB.maintenance_event.insert(maintenance_event=maintenance_event)
    
    
    
    

@router.get("/q")
def get_maintenance_events(instrument_tag : str = None, user_tag : str = None, timestamp_min : float = None, timestamp_max : float = None, limit : int = 20, order_by_time : bool = True, user: UserModel = Depends(get_user_from_token)) -> List[str]:
    """Returns a list of maintenance events."""
    return DB.maintenance_event.find(instrument_tag=instrument_tag, 
                                    user_tag=user_tag,
                                    timestamp_min=timestamp_min,
                                    timestamp_max=timestamp_max,
                                    limit=limit,
                                    order_by_time=order_by_time)

# @router.get("/q")
# def find_maintenance(search_string : str = "", limit : int = None) -> List[str]:
#     """Finds maintenance events by a search_string and returns the tags. 
#     """    
#     return DB.maintenance.find(search_string = search_string, limit = limit)

@router.get("/count")
def get_maintenance_event_counts(instrument_tag : str = None, user_tag : str = None, timestamp_min : float = None, timestamp_max : float = None, user: UserModel = Depends(get_user_from_token)) -> int:
    count = DB.maintenance_event.count(instrument_tag = instrument_tag, user_tag = user_tag, timestamp_min = timestamp_min, timestamp_max = timestamp_max)
    return count 


@router.get("/states")
def get_maintenance_states():
    """Returns all maintenance states."""
    return DB.maintenance_event.get_states()

@router.get("/{tag}")
def get_maintenance_event_by_tag(tag : str):
    """
    Returns a maintenance event by a tag.
    """
    print("I AM DOING THIS")
    maintenance = DB.maintenance_event.get(tag = tag)
    print(maintenance)
    if not maintenance:
        raise HTTPException(status_code=404, detail="Maintenance entry not found.")
    return maintenance

@router.get("/{maintenance_event_tag}/state")
def get_maintenance_event_state(maintenance_event_tag : str):
    """Returns the state of a maintenance event by its tag."""
    if not DB.maintenance_event.exists(tag = maintenance_event_tag):
        raise HTTPException(status_code=404, detail="Maintenance event not found.")
    
    return DB.maintenance_event.get_event_state(tag = maintenance_event_tag)




@router.post("/{maintenance_event_tag}/state/{state_tag}")
def set_maintenance_event_state(maintenance_event_tag : str, state_tag : str, user : UserModel = Depends(is_user_at_least_curator)):
    """Sets the state of a maintenance event. 
    If the maintenance event does not exist, it will raise a 404 error.
    If the state does not exist, it will raise a 404 error.
    """
    if not DB.maintenance_event.exists(tag = maintenance_event_tag):
        raise HTTPException(status_code=404, detail="Maintenance event not found.")
    
    DB.maintenance_event.set_state(tag = maintenance_event_tag, state_tag = state_tag, user_tag = user.tag, description = "State changed by user {}".format(user.firstname))

@router.post("/{maintenance_event_tag}/symptoms")
def add_symptom_to_maintenance_event(maintenance_event_tag : str, symptom_tags : List[str], user : UserModel = Depends(is_user_at_least_curator)):
    """Adds symptoms to a maintenance event. This will replace any existing symptoms for the event.
    If you want to add symptoms without replacing existing ones, use the / method instead. 
    """
    if not DB.maintenance.exists(tag = maintenance_event_tag):
        raise HTTPException(status_code=404, detail="Maintenance event not found.")
    DB.maintenance_event.remove_symptoms(tag = maintenance_event_tag) # Clear existing symptoms before adding new ones
    DB.maintenance_event.add_symptoms(tag = maintenance_event_tag, symptoms = symptom_tags)
    

@router.post("/{maintenance_event_tag}/procedures/{maintenance_procedure_tag}")
def add_procedure_to_maintenance_event(maintenance_event_tag : str,  maintenance_procedure_tag : str, user : UserModel = Depends(is_user_at_least_curator)):
    """Adds a single procedure to a maintenance event. 
    If the maintenance event does not exist, it will raise a 404 error.
    If the procedure does not exist, it will raise a 404 error.
    """
    if not DB.maintenance_event.exists(tag = maintenance_event_tag):
        raise HTTPException(status_code=404, detail="Maintenance event not found.")
    if not DB.maintenance_procedures.exists(tag =  maintenance_procedure_tag):
        raise HTTPException(status_code=404, detail="Procedure not found.")
    
    DB.maintenance_event.add_maintenance_procedure(tag = maintenance_event_tag,  maintenance_procedure_tag =  maintenance_procedure_tag, user_tag = user.tag) 
    
    
@router.delete("/{maintenance_event_tag}/procedures/{maintenance_procedure_tag}")
def remove_procedure_from_maintenance_event(maintenance_event_tag : str,  maintenance_procedure_tag : str, user : UserModel = Depends(is_user_at_least_curator)):
    """Removes a single! procedure from a maintenance event.
    If the procedure is not associated with the maintenance event, it will do nothing.
    If the maintenance event does not exist, it will raise a 404 error.
    If the procedure does not exist, it will raise a 404 error.
    """       
    if not DB.maintenance_event.exists(tag = maintenance_event_tag):
        raise HTTPException(status_code=404, detail="Maintenance event not found.")
    if not DB.maintenance_procedures.exists(tag =  maintenance_procedure_tag):
        raise HTTPException(status_code=404, detail="Procedure not found.")
    # remove procedure from the maintenance event
    DB.maintenance_event.remove_maintenance_procedure(tag = maintenance_event_tag,  maintenance_procedure_tag = maintenance_procedure_tag)


@router.post("/{maintenance_event_tag}/symptoms/{symptom_tag}")
def add_symptom_to_maintenance_event_by_tag(maintenance_event_tag : str, symptom_tag : str, user : UserModel = Depends(is_user_at_least_curator)):
    """Adds a single symptom to a maintenance event. 
    """
    if not DB.maintenance_event.exists(tag = maintenance_event_tag):
        raise HTTPException(status_code=404, detail="Maintenance event not found.")
    if not DB.symptoms.exists(tag = symptom_tag):
        raise HTTPException(status_code=404, detail="Symptom not found.")
    
    DB.maintenance_event.add_symptom(tag = maintenance_event_tag, symptom_tag = symptom_tag)


@router.delete("/{maintenance_event_tag}/symptoms/{symptom_tag}")
def remove_symptom_from_maintenance_event(maintenance_event_tag : str, symptom_tag : str, user : UserModel = Depends(is_user_at_least_curator)):
    """Removes a single! symptom from a maintenance event.
    If the symptom is not associated with the maintenance event, it will do nothing.
    If the maintenance event does not exist, it will raise a 404 error.
    If the symptom does not exist, it will raise a 404 error.
    """
    if not DB.maintenance_event.exists(tag = maintenance_event_tag):
        raise HTTPException(status_code=404, detail="Maintenance event not found.")
    if not DB.symptoms.exists(tag = symptom_tag):
        raise HTTPException(status_code=404, detail="Symptom not found.")
    # remove symtom from the maintenance event
    DB.maintenance_event.remove_symptom(tag = maintenance_event_tag, symptom_tag = symptom_tag)  


@router.delete("/{maintenance_event_tag}/spareparts/{sparepart_tag}")
def remove_sparepart_from_maintenance_event(maintenance_event_tag : str, sparepart_tag : str, user : UserModel = Depends(is_user_at_least_curator)):
    """Removes a single! symptom from a maintenance event.
    If the symptom is not associated with the maintenance event, it will do nothing.
    If the maintenance event does not exist, it will raise a 404 error.
    If the symptom does not exist, it will raise a 404 error.
    """
    if not DB.maintenance_event.exists(tag = maintenance_event_tag):
        raise HTTPException(status_code=404, detail="Maintenance event not found.")
    if not DB.spareparts.exists(tag = sparepart_tag):
        raise HTTPException(status_code=404, detail="Spare part not found.")
    # remove symtom from the maintenance event
    DB.maintenance_event.remove_sparepart(tag = maintenance_event_tag, sparepart_tag = sparepart_tag)  


@router.post("/{maintenance_event_tag}/spareparts/{sparepart_tag}")
def add_symptom_to_maintenance_event_by_tag(maintenance_event_tag : str, sparepart_tag : str, user : UserModel = Depends(is_user_at_least_curator)):
    """Adds a single symptom to a maintenance event. 
    """
    if not DB.maintenance_event.exists(tag = maintenance_event_tag):
        raise HTTPException(status_code=404, detail="Maintenance event not found.")
    if not DB.spareparts.exists(tag = sparepart_tag):
        raise HTTPException(status_code=404, detail="Spare part not found..")
    
    DB.maintenance_event.add_sparepart(tag = maintenance_event_tag, sparepart_tag = sparepart_tag)



@router.get("/{maintenance_event_tag}/spareparts/{sparepart_tag}/count")
def get_sparepart_count_in_maintenance_event(maintenance_event_tag : str, sparepart_tag : str, user : UserModel = Depends(get_user_from_token)) -> int:
    """Returns the count of a spare part in a maintenance event.
    If the maintenance event does not exist, it will raise a 404 error.
    If the spare part does not exist, it will raise a 404 error.
    """
    if not DB.maintenance_event.exists(tag = maintenance_event_tag):
        raise HTTPException(status_code=404, detail="Maintenance event not found.")
    if not DB.spareparts.exists(tag = sparepart_tag):
        raise HTTPException(status_code=404, detail="Spare part not found.")
    
    count = DB.maintenance_event.get_sparepart_count(tag = maintenance_event_tag, sparepart_tag = sparepart_tag)
    return count


#this should be renamed as the instrument tag is not the same as the maintenance tag
@router.get("/instruments/{instrument_tag}/costs")
def get_costs_by_instrument(instrument_tag : str, timestamp_min : float = None, timestamp_max : float = None, user : UserModel = Depends(get_user_from_token)):
    """Returns the total costs for a given instrument. 
    """
    costs = DB.maintenance_event.costs(instrument_tag = instrument_tag, timestamp_min = timestamp_min, timestamp_max = timestamp_max)
    if costs is None:
        raise HTTPException(status_code=404, detail="No maintenance events found for this instrument.")
    return costs 



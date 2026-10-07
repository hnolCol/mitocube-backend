from typing import List 
from lib.database.Database import get_db
from lib.database.abstract.Database import DatabaseABC

from fastapi import APIRouter, Depends, HTTPException


from config.models.user import UserModel
from config.models.maintenance import ExternalServiceBaseModel, ExternalServiceInsertModel, ExternalServiceModel
from services.users import is_user_admin, get_user_from_token, is_user_at_least_curator



router = APIRouter(dependencies=[Depends(get_user_from_token)],
    prefix="/api/maintenance/externalservice",
    tags=["Maintenance", "Service"]
    )

@router.get("/q")
def find_external_services(search_string : str = None, limit : int = 20, db : DatabaseABC = Depends(get_db)) -> List[str]:
    "Finds external services by a search_string and returns the tags. " 
    tags = db.external_service.find(search_string = search_string, limit = limit)
    return tags

@router.get("/{tag}")
def get_external_service(tag : str, db : DatabaseABC = Depends(get_db)) -> ExternalServiceModel:
    """Get a external service by its tag."""

    if not db.external_service.exists(tag):
        raise HTTPException(status_code=404, detail="External Service not found")

    return db.external_service.get(tag= tag)

@router.post("/")
def insert_external_service(service :ExternalServiceInsertModel, maintenance_event_tag : str = None, user: UserModel = Depends(is_user_admin), db : DatabaseABC = Depends(get_db)) -> str:
    """Insert a new external service. Returns the tag of the inserted service."""


    ok = db.external_service.insert(service=service, user_tag=user.tag)
    
    if maintenance_event_tag is not None:
        db.maintenance_events.add_external_service(tag = maintenance_event_tag, external_service_tag= service.tag)
    if not ok:
        raise HTTPException(status_code=500, detail="Could not insert external service.")
    
    return service.tag

@router.delete("/{tag}")
def delete_external_service(tag: str, user: UserModel = Depends(is_user_at_least_curator), db : DatabaseABC = Depends(get_db)) -> bool:
    """Deletes an external maintenance service"""

    if not db.external_service.exists(tag):
        raise HTTPException(status_code=404, detail="External Service not found.")
    
    ok = db.external_service.delete(tag= tag)
    return ok 

@router.put("/{tag}", response_model=bool)
def update_external_service( service : ExternalServiceModel, user: UserModel = Depends(is_user_admin), db : DatabaseABC = Depends(get_db)) -> bool:
    """Update an external service in the database."""

    ok = db.external_service.update(service=service, user_tag=user.tag)

    if not ok:
        raise HTTPException(status_code=500, detail="Could not update external service.")
    
    return ok

@router.get("/{tag}/description")
def get_description(tag: str, db : DatabaseABC = Depends(get_db)) -> str:
    """
    Get the description of the external service by its tag. 
    """

    if not db.external_service.exists(tag= tag):
        raise HTTPException(status_code=404, detail="External service not found.")
    
    return db.external_service.get_description(tag= tag)

@router.get("/{tag}/name")
def get_name(tag: str, db : DatabaseABC = Depends(get_db)) -> str:
    """
    Get the name of the person that provided the service by its tag.
    """
    if not db.external_service.exists(tag= tag):
        raise HTTPException(status_code=404, detail="External service not found.")
    
    return db.external_service.get_name(tag= tag)

@router.get("/{tag}/company")
def get_company(tag: str, db : DatabaseABC = Depends(get_db)) -> str:
    """
    Get the company name providing the service.
    """

    if not db.external_service.exists(tag= tag):
        raise HTTPException(status_code=404, detail="External service not found.")
    
    return db.external_service.get_company(tag= tag)

@router.get("/{tag}/email")
def get_email(tag: str, db : DatabaseABC = Depends(get_db)) -> str:
    """
    Get the contact person's email address. 
    """

    if not db.external_service.exists(tag= tag):
        raise HTTPException(status_code=404, detail="External service not found.")
    
    return db.external_service.get_email(tag= tag)


@router.get("/{tag}/costs")
def get_costs(tag: str, db : DatabaseABC = Depends(get_db)) -> float | int:
    """
    Get costs of the service
    """

    if not db.external_service.exists(tag= tag):
        raise HTTPException(status_code=404, detail="External service not found.")
    
    return db.external_service.get_costs(tag= tag)


@router.get("/{tag}/billing_number")
def get_billing_number(tag: str, db : DatabaseABC = Depends(get_db)) -> str:
    """
    Get the billing or invoice number. 
    """

    if not db.external_service.exists(tag= tag):
        raise HTTPException(status_code=404, detail="External service not found.")
    
    return db.external_service.get_billing_number(tag= tag)


@router.get("/{tag}/internal_id")
def internal_id(tag: str, db : DatabaseABC = Depends(get_db)) -> str:
    """
    Get Internal ID for the service. 
    """

    if not db.external_service.exists(tag= tag):
        raise HTTPException(status_code=404, detail="External service not found.")
    
    return db.external_service.get_internal_id(tag= tag)


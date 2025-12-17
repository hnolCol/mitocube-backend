from typing import List 

from fastapi import APIRouter, Depends, HTTPException

from lib.database.Database import Database

from config.models.user import UserModel
from config.models.maintenance import ExternalServiceBaseModel, ExternalServiceInsertModel, ExternalServiceModel
from services.users import is_user_admin, get_user_from_token


DB = Database.DB()

router = APIRouter(
    prefix="/api/maintenance/externalservice",
    tags=["Maintenance", "Service"]
    )

@router.get("/{tag}")
def get_external_service(tag : str) -> ExternalServiceModel:
    """Get a external service by its tag."""

    if not DB.external_service.exists(tag = tag):
        raise HTTPException(status_code=404, detail="External Service not found")

    return DB.external_service.get(tag= tag)

@router.post("/", response_model=bool)
def insert_external_service(service : ExternalServiceInsertModel, user: UserModel = Depends(is_user_admin)) -> bool:
    """Insert a new external service"""

    ok = DB.external_service.insert(service, user_tag=user.tag)

    if not ok:
        raise HTTPException(status_code=500, detail="Could not insert external service.")
    
    return ok 

@router.delete("/{tag}")
def delete_external_service(tag: str) -> bool:
    """Deletes an external maintenance service"""

    if not DB.external_service.exists(tag):
        raise HTTPException(status_code=404, detail="External Service not found.")
    
    ok = DB.external_service.delete(tag= tag)
    return ok 

@router.put("/{tag}", response_model=bool)
def update_external_service( service : ExternalServiceModel, user: UserModel = Depends(is_user_admin)) -> bool:
    """Update an external service in the database."""

    ok = DB.external_service.update(service=service, user_tag=user.tag)

    if not ok:
        raise HTTPException(status_code=500, detail="Could not update external service.")
    
    return ok

@router.get("/{tag}/description")
def get_description(tag: str) -> str:
    """
    Get the description of the external service by its tag. 
    """

    if not DB.external_service.exists(tag= tag):
        raise HTTPException(status_code=404, detail="External service not found.")
    
    return DB.external_service.get_description(tag= tag)

@router.get("/{tag}/name")
def get_name(self, tag: str) -> str:
    """
    Get the name of the person that provided the service by its tag.
    """
    if not DB.external_service.exists(tag= tag):
        raise HTTPException(status_code=404, detail="External service not found.")
    
    return DB.external_service.get_name(tag= tag)

@router.get("/{tag}/company")
def get_company(self, tag: str) -> str:
    """
    Get the company name providing the service.
    """

    if not DB.external_service.exists(tag= tag):
        raise HTTPException(status_code=404, detail="External service not found.")
    
    return DB.external_service.get_company(tag= tag)

@router.get("/{tag}/email")
def get_email(self, tag: str) -> str:
    """
    Get the contact person's email address. 
    """

    if not DB.external_service.exists(tag= tag):
        raise HTTPException(status_code=404, detail="External service not found.")
    
    return DB.external_service.get_email(tag= tag)


@router.get("/{tag}/cost")
def get_cost(self, tag: str) -> float | int:
    """
    Get cost of the service
    """

    if not DB.external_service.exists(tag= tag):
        raise HTTPException(status_code=404, detail="External service not found.")
    
    return DB.external_service.get_cost(tag= tag)


@router.get("/{tag}/billing_number")
def get_billing_number(self, tag: str) -> str:
    """
    Get the billing or invoice number. 
    """

    if not DB.external_service.exists(tag= tag):
        raise HTTPException(status_code=404, detail="External service not found.")
    
    return DB.external_service.get_billing_number(tag= tag)


@router.get("/{tag}/internal_id")
def internal_id(self, tag: str) -> str:
    """
    Get Internal ID for the service. 
    """

    if not DB.external_service.exists(tag= tag):
        raise HTTPException(status_code=404, detail="External service not found.")
    
    return DB.external_service.get_internal_id(tag= tag)

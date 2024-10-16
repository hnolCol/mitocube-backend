from typing import List, Dict
import warnings

from fastapi import APIRouter, Depends, Request, BackgroundTasks
from fastapi.exceptions import HTTPException

from lib.rest.security import rest_verify_user_token, RestSessionInformation


router = APIRouter(prefix="/api/user", tags=["User"])

@router.get("/{username}")  # , response_model=AttributeResponseModel)
def rest_get_user_profile(session: RestSessionInformation = Depends(rest_verify_user_token)):
    pass  # ToDo: implement router.get("/{username}")

@router.get("/{username}/detailed")  # , response_model=AttributeResponseModel)
def rest_get_detailed_user_profile(session: RestSessionInformation = Depends(rest_verify_user_token)):
    pass  # ToDo: implement router.get("/{username}/detailed")

@router.post("/{username}")  # , response_model=AttributeResponseModel)
def rest_post_update_user_profile(session: RestSessionInformation = Depends(rest_verify_user_token)):
    pass  # ToDo: implement router.post("/{username}")

@router.post("/{username}/pw")  # , response_model=AttributeResponseModel)
def rest_post_update_user_password(session: RestSessionInformation = Depends(rest_verify_user_token)):
    pass  # ToDo: implement router.post("/{username}/pw")

@router.get("/{username}/image")  # , response_model=AttributeResponseModel)
def rest_get_user_image(session: RestSessionInformation = Depends(rest_verify_user_token)):
    pass  # ToDo: implement router.get("/{username}/image")

@router.post("/{username}/image")  # , response_model=AttributeResponseModel)
def rest_post_user_image(session: RestSessionInformation = Depends(rest_verify_user_token)):
    pass  # ToDo: implement router.post("/{username}/image")

@router.get("/{username}/role")  # , response_model=AttributeResponseModel)
def rest_get_user_image(session: RestSessionInformation = Depends(rest_verify_user_token)):
    pass  # ToDo: implement router.get("/{username}/role")

@router.delete("/{username}")  # , response_model=AttributeResponseModel)
def rest_delete_deactivate_user_profile(session: RestSessionInformation = Depends(rest_verify_user_token)):
    pass  # ToDo: implement router.delete("/{username}")




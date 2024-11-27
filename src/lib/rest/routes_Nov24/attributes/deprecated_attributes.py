from typing import Any, List, Dict
import warnings

from fastapi import APIRouter, Depends, Request, BackgroundTasks, status
from fastapi.exceptions import HTTPException

import lib.data as dlib

from lib.rest.security import rest_verify_user_token, RestSessionInformation

router = APIRouter(prefix="/api/attributes", tags=["Attributes", "Traits", "Deprecated"])

def deprecated_api(message):  # ToDo: Replace with from warnings import deprecated; @deprecated with python 3.13
    warnings.warn(message, DeprecationWarning, stacklevel=2)


# ToDo: Next
# INFO:     127.0.0.1:49582 - "GET /api/users/roles HTTP/1.1" 404 Not Found
#
# @router.post("/q", deprecated=True)
# def rest_get_query_attributes(labels : str, count : bool = True, max_attributes : int = 999999):
#     pass
#
# @router.get("/attribute_values/q", deprecated=True)
# def rest_get_query_traits(labels: str = None, attribute_value_tag: str = None, attribute_tag: str = None,
#                           count: bool = True, max_attributes: int = 999999):
#     pass

from typing import List, Annotated, Literal, Dict, Type
import time
import string
import random

from datetime import datetime
import warnings

import lib.data as dlib
import lib.data.sql.postgresql as psql
import psycopg2


from lib.rest.security import RestPermissionSteward, RestSessionInformation

from fastapi import APIRouter, Depends, Request, BackgroundTasks, status
from fastapi.exceptions import HTTPException

router = APIRouter(prefix="/api/submission", tags=["Datasets", "Deprecated"])

def deprecated_api(message):  # ToDo: Replace with from warnings import deprecated; @deprecated with python 3.13
    warnings.warn(message, DeprecationWarning, stacklevel=2)

@router.get("/id", deprecated=True)  # ToDo: Write PTM  # Deprecated, why? user should choose by themself or it is assigned when first submitted. Wrong path, submission versus submissions in old backend
def rest_get_generate_new_submission_id():
    """
    A unique id that cannot be changed for a project/data/submission.
    """
    ds: Type[dlib.ABCDataset] = dlib.ABCDataset.get_class()
    it = 0
    character_scope = string.ascii_letters + string.digits

    while True:
        it += 1
        # new_label = "".join([character_scope[random.randint(0, len(character_scope))] for ix in range(random.randint(8, 12))])
        new_label = "".join([character_scope[random.randint(0, len(character_scope)-1)] for ix in range(10)])
        if not ds.does_exist_with_label(label = new_label):
            break
        elif it > 42:
            raise dlib.ABCDatasetError("Unable to generate a new random and unique dataset label. Try again...")

    return {"id": new_label, "created_on": datetime.now(tz=None)}  # Question, Why is created_on here?

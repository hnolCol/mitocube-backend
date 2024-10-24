from typing import Any, Dict, List
import json

from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates

from config import SystemSettings

import lib.data as dlib

from lib.rest.security import rest_verify_user_token, RestSessionInformation


router = APIRouter(prefix="", tags=["App Information"])

# Question, make this expire-able or move to rest_fronted() so one does not have to restart?
frontend_client = Jinja2Templates(directory = "/home/andreaslindner/Projects/MitoCube/GitHub/mitocube-frontend/dist")


@router.get("/", include_in_schema = True)
async def rest_get_frontend(request: Request):
    return frontend_client.TemplateResponse("index.html", {"request": request})


@router.get("/api/info/app",
            summary = "Returns basic information about the application.")
def rest_get_application_info():  # ToDo: Implement PRM
    """"""
    system_settings = SystemSettings.get_system_settings()

    return {"app_name": system_settings.app_name,
            "app_description": system_settings.app_description,
            "version": system_settings.app_version,
            "lead_contact": system_settings.app_lead_contact}

@router.get("/api/info/keyfigures",  # Question: rename to /api/info/dashboard_stats?
            summary="Returns the key figures of the backend")
def rest_get_db_stats(session: RestSessionInformation = Depends(rest_verify_user_token)) -> List[Dict[str, Any]]:  # ToDo: Create PRM

    db = dlib.ABCStatDatabase.get_class()()
    key_figures: List[Dict[str, Any]] = list()

    # if KEY_FIGURE_SETTINGS.number_submissions:  # Question: Configurable?
    key_figures.append({"label": "Submissions",
                        "metric": db.get_n_submissions()})
    # if KEY_FIGURE_SETTINGS.number_published_datasets:
    # published_datasets = db_helper.get_label_count_by_state(k_subset=set([SubmissionStates.PUBLISHED]))[SubmissionStates.PUBLISHED]["submission_count"]
    key_figures.append({"label": "Published Data",
                        "metric": db.get_n_active_datasets()})
    # if KEY_FIGURE_SETTINGS.number_proteins:
    key_figures.append({"label": "Proteins",
                        "metric": db.get_n_pg_features()})
    # if KEY_FIGURE_SETTINGS.number_genotypes:
    key_figures.append({"label": "Genotypes",
                        "metric": db.get_n_genotypes()})
    # if KEY_FIGURE_SETTINGS.number_users:
    key_figures.append({"label": "Users", "metric": db.get_n_active_users()})

    return key_figures


@router.get("/api/info/terms")
def rest_get_terms_of_use():  # ToDo, Add Typing for return value
    system_settings = SystemSettings.get_system_settings()

    with open(system_settings.app_json_use_terms, "r") as in_file:
        return json.load(in_file)

# ToDo: Add Route for _Impressum_
# ToDo: Add Route for Contact

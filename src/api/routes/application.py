from typing import Any, Dict, List
# from collections import OrderedDict

from fastapi import APIRouter, Request  # Depends, BackgroundTasks
from fastapi.templating import Jinja2Templates

from lib.data.sql.postgresql import PostgreSQLDatabase

from api.pmodels.application import ApplicationInformationPModel



router = APIRouter(prefix="",
                   tags=["App Information"])


# host the static html of the frontend
# ToDo: Look Jinja2Templates up
frontend_client = Jinja2Templates(directory = "/home/andreaslindner/Projects/MitoCube/GitHub/mitocube-frontend/dist")

@router.get("/", include_in_schema = True)
async def frontend(request: Request):
    return frontend_client.TemplateResponse("index.html", {"request": request})

@router.get("/api/info/app",summary = "Returns basic information about the application.", response_model = ApplicationInformationPModel)
def get_application_info():  # ToDo: Implement
    """"""
    return ApplicationInformationPModel(backend_version = "γάμμα",
                                        something = "Why couldn’t the tree get on his computer? Because he could not log on.")


@router.get("/info/keyfigures", summary="Returns the key figures of the backend")
# def get_keyfigures(user: UserModel = Depends(get_user_from_token)):  # ToDo: check for simple login
def get_db_stats() -> List[Dict[str, Any]]:  # ToDo: Create PRM
    key_figures: List[Dict[str, Any]] = list()

    # if KEY_FIGURE_SETTINGS.number_submissions:
    key_figures.append({"label": "Submissions",
                        "metric": PostgreSQLDatabase.get_n_submissions()})  # ToDo: len(db_helper.get_all_labels())
    # if KEY_FIGURE_SETTINGS.number_published_datasets:
    # published_datasets = db_helper.get_label_count_by_state(k_subset=set([SubmissionStates.PUBLISHED]))[SubmissionStates.PUBLISHED]["submission_count"]
    key_figures.append({"label": "Published Data",
                        "metric": PostgreSQLDatabase.get_n_active_datasets()})  # ToDo: Rename to ActiveData, published_datasets
    # if KEY_FIGURE_SETTINGS.number_proteins:
    key_figures.append({"label": "Proteins",
                        "metric": PostgreSQLDatabase.get_n_pg_features()})  # ToDo: db_helper.get_number_features()
    # if KEY_FIGURE_SETTINGS.number_genotypes:
    key_figures.append({"label": "Genotypes",
                        "metric": PostgreSQLDatabase.get_n_genotypes()})  # ToDo: db_helper.get_number_genotypes()
    # if KEY_FIGURE_SETTINGS.number_users:
    key_figures.append(
        {"label": "Users",
         "metric": PostgreSQLDatabase.get_n_active_users()})  # ToDo: UserDB.get_number_of_users()

    return key_figures

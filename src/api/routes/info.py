from fastapi import APIRouter # Depends, Request, BackgroundTasks

from api.pmodels.info import ApplicationInformationPModel

router = APIRouter(
    prefix="/api",
    tags=["App Information"],
    )
@router.get("/info/app",summary = "Returns basic information about the application.", response_model = ApplicationInformationPModel)
def get_application_info():
    """"""
    return ApplicationInformationPModel(backend_version = "γάμμα",
                                        something = "Why couldn’t the tree get on his computer? Because he could not log on.")

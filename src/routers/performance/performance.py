from typing import List 

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException

from lib.database.Database import Database

from config.models.user import UserModel
from config.models.performance import QCPeptidesModel, QCPeptideModel
from services.users import is_user_admin, get_user_from_token

from routers.performance import runs as performance_runs

router = APIRouter(dependencies=[Depends(get_user_from_token)],
    prefix="/api/performance",
    tags=["Performance"]
    )


DB = Database.DB()



@router.post("")
def post_performance_run(user : UserModel = Depends(is_user_admin)):
    ""


@router.get("/")
def get_performance_runs():
    ""


@router.get("/metrices")
def get_performance_metrices():
    """Returns the metrices that have to be specified. 
    """
    #TO DO: fix this to make it definable.  , make it an attribute ?
    
    return [{"text" : "quant_proteins","description": "The number of quantified proteins"}, 
            {"text" : "quant_peptides","description" : "Number of quantified peptides."}]

@router.get("/peptides")
def get_performance_metrices() -> List[QCPeptideModel]:
    """Returns the peptides for which the retention time 
    should be recorded for a qc run. 
    """
    return DB.peptides.get_qc_peptides()


@router.post("/peptides")
def add_qc_peptides(peptides : QCPeptidesModel, user : UserModel = Depends(is_user_admin)):
    "Add peptides to the database that are used to run quality control"
    
    DB.peptides.set_qc_peptides()
    
    
    
    

    
router.include_router(performance_runs.router)

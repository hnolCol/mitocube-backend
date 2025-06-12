from typing import List 

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException

from lib.database.Database import Database

from config.models.performance import QCRunModel
from config.models.user import UserModel
from config.models.performance import QCPeptidesModel, QCPeptideModel
from services.users import is_user_admin, get_user_from_token

router = APIRouter(
    prefix="/api/performance",
    tags=["Performance"]
    )


DB = Database.DB()



@router.post("")
def post_performance_run():
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
    
    
    
    

    
@router.get("runs/q")
def query_performance_runs():
    ""

@router.get("/runs/{run_label}")
def get_performance_run(run_label : str):
    ""
@router.post("/runs")
def add_performance_run():
    ""
    

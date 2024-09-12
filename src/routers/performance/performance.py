from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException

router = APIRouter(
    prefix="/api/performance",
    tags=["Performance"]
    )



@router.post("")
def post_performance_run():
    ""


@router.get("/")
def get_performance_runs():
    ""
    
    
@router.get("runs/q")
def query_performance_runs():
    ""

@router.get("/runs/{run_label}")
def get_performance_run(run_label : str):
    ""
@router.post("/runs")
def add_performance_run():
    ""
    

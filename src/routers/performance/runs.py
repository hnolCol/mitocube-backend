from typing import List
from fastapi import APIRouter, Depends, HTTPException
from lib.database.Database import Database
from config.models.performance import QCRunInsertModel, QCRunResponseModel, QCPrecursorInsertModel, QCPrecursorResponseModel
from config.models.user import UserModel
from services.users import is_user_at_least_curator, get_user_from_token

router = APIRouter(dependencies=[Depends(get_user_from_token)],
    prefix="/api/performance",
    tags=["Performance"]
)

DB = Database.DB()


@router.get("/runs", summary="Returns the QC runs.")
def get_performance_runs(instrument_name_tag : str = None, qc_standard_tag : str = None, limit : int = 50, user : UserModel = Depends(is_user_at_least_curator)) -> List[QCRunResponseModel]:
    """
    Returns the QC runs, optionally filtered by instrument and QC standard.

    Parameters
    ----------
    instrument_name_tag : str, optional
        The tag of the instrument the runs were acquired on, by default None
    qc_standard_tag : str, optional
        The tag of the QC standard that was used to generate the runs, by default None
    limit : int, optional
        The maximum number of runs to return, by default 50
    user : UserModel, optional
        The user that is extracted by the token, by default Depends(is_user_at_least_curator)

    Returns
    -------
    List[QCRunResponseModel]
        The QC runs.
    """
    return DB.qc.get(instrument_name_tag = instrument_name_tag, qc_standard_tag = qc_standard_tag, limit = limit)


@router.get("/runs/count", summary="Counts the QC runs.")
def count_performance_runs(by_instrument : bool = False, user : UserModel = Depends(is_user_at_least_curator)):
    """
    Counts the QC runs, optionally grouped by instrument.

    Parameters
    ----------
    by_instrument : bool, optional
        If true, the number of runs is counted per instrument, by default False
    user : UserModel, optional
        The user that is extracted by the token, by default Depends(is_user_at_least_curator)

    Returns
    -------
    int | List[Tuple[str,int]]
        The number of runs or a list of instrument tag and count tuples.
    """
    return DB.qc.count(by_instrument = by_instrument)


@router.get("/runs/{run_tag}", summary="Returns a QC run by its tag.")
def get_performance_run(run_tag : str, user : UserModel = Depends(is_user_at_least_curator)) -> QCRunResponseModel:
    """
    Returns a QC run by its tag.

    Parameters
    ----------
    run_tag : str
        The tag of the run.
    user : UserModel, optional
        The user that is extracted by the token, by default Depends(is_user_at_least_curator)

    Returns
    -------
    QCRunResponseModel
        The run.

    Raises
    ------
    HTTPException
        If the run does not exist.
    """
    if not DB.qc.exists(tag = run_tag): raise HTTPException(status_code=404, detail=f"QC run with tag {run_tag} not found.")
    runs = DB.qc.get(tags = [run_tag], limit = 1)
    if not runs: raise HTTPException(status_code=404, detail=f"QC run with tag {run_tag} not found.")
    return runs[0]


@router.post("/runs/insert", summary="Inserts a QC run. Requires at least curator rights.")
def insert_performance_run(run : QCRunInsertModel, user : UserModel = Depends(is_user_at_least_curator)) -> bool:
    """
    Inserts a QC run into the database. The run is linked to the instrument it was
    acquired on and to the QC standard that was used to generate it.

    Parameters
    ----------
    run : QCRunInsertModel
        The run to insert.
    user : UserModel, optional
        The user that is extracted by the token, by default Depends(is_user_at_least_curator)

    Returns
    -------
    bool
        True if the run was inserted.

    Raises
    ------
    HTTPException
        If the QC standard does not exist (404).
    """
    if not DB.qc.standard_exists(tag = run.qc_standard_tag): raise HTTPException(status_code=404, detail=f"QC standard with tag {run.qc_standard_tag} not found.")
    return DB.qc.insert(performance_run = run)


@router.post("/runs/{run_tag}/precursors", summary="Adds quantified QCPrecursors to a QC run. Requires at least curator rights.")
def add_qc_precursors(run_tag : str, precursors : List[QCPrecursorInsertModel], user : UserModel = Depends(is_user_at_least_curator)) -> bool:
    """
    Adds the quantified QCPrecursors to a QC run. The precursors are linked to the run via
    a [:QUANTIFIED] relationship that carries the intensity, score and retention time
    of the precursor in this specific run, consistent with the Sample-[:QUANTIFIED]->Precursor
    pattern of the biological quantifications. Only a specific subset of precursors is recorded
    for QC, the full quantification data is not uploaded since it has no biological meaning
    and is too large. Precursors that do not exist in the database are skipped.

    Parameters
    ----------
    run_tag : str
        The tag of the QC run the precursors belong to.
    precursors : List[QCPrecursorInsertModel]
        The precursors with their intensity, score and retention time.
    user : UserModel, optional
        The user that is extracted by the token, by default Depends(is_user_at_least_curator)

    Returns
    -------
    bool
        True if the precursors were added.

    Raises
    ------
    HTTPException
        If the run does not exist (404) or no precursors are provided (400).
    """
    if not DB.qc.exists(tag = run_tag): raise HTTPException(status_code=404, detail=f"QC run with tag {run_tag} not found.")
    if len(precursors) == 0: raise HTTPException(status_code=400, detail="No precursors provided.")
    return DB.qc.insert_qc_precursors(run_tag = run_tag, precursors = precursors)


@router.get("/runs/{run_tag}/precursors", summary="Returns the QCPrecursors of a QC run.")
def get_qc_precursors(run_tag : str, user : UserModel = Depends(is_user_at_least_curator)) -> List[QCPrecursorResponseModel]:
    """
    Returns the QCPrecursors that were recorded for a QC run.

    Parameters
    ----------
    run_tag : str
        The tag of the QC run.
    user : UserModel, optional
        The user that is extracted by the token, by default Depends(is_user_at_least_curator)

    Returns
    -------
    List[QCPrecursorResponseModel]
        The recorded precursors of the run.

    Raises
    ------
    HTTPException
        If the run does not exist.
    """
    if not DB.qc.exists(tag = run_tag): raise HTTPException(status_code=404, detail=f"QC run with tag {run_tag} not found.")
    return DB.qc.get_qc_precursors(run_tag = run_tag)


@router.delete("/runs/{run_tag}", summary="Deletes a QC run. Requires at least curator rights.")
def delete_performance_run(run_tag : str, user : UserModel = Depends(is_user_at_least_curator)) -> bool:
    """
    Deletes a QC run and all its relationships.

    Parameters
    ----------
    run_tag : str
        The tag of the run to delete.
    user : UserModel, optional
        The user that is extracted by the token, by default Depends(is_user_at_least_curator)

    Returns
    -------
    bool
        True if the run was deleted.

    Raises
    ------
    HTTPException
        If the run does not exist.
    """
    if not DB.qc.exists(tag = run_tag): raise HTTPException(status_code=404, detail=f"QC run with tag {run_tag} not found.")
    return DB.qc.delete(tag = run_tag)

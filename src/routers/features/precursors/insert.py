from fastapi import APIRouter, Depends, HTTPException
from typing import List
from config.models.user import UserModel
from services.users import is_user_at_least_curator, get_user_from_token
from lib.database.Database import Database
from config.models.precursors import PrecursorInsertModel

DB = Database.DB()

router = APIRouter(
    prefix="/api/features/precursors",
    tags=["Features", "Precursors"]
)


@router.post("/insert", summary="Inserts a precursor into the database. Requires curator rights.")
def insert_precursor(precursor : PrecursorInsertModel, user : UserModel = Depends(is_user_at_least_curator)) -> bool:
    """
    Inserts a precursor into the database. The precursor tag is derived from the
    peptide sequence and the charge state (sequence.charge). The precursor is connected
    to the given protein group. Requires curator rights.

    Parameters
    ----------
    precursor : PrecursorInsertModel
        The precursor to insert.
    user : UserModel, optional
        The user that is extracted by the token, by default Depends(is_user_at_least_curator)

    Returns
    -------
    bool
        True if the insertion was successful, False otherwise.

    Raises
    ------
    HTTPException
        If the protein group with the given tag does not exist.
    """
    if not DB.protein_groups.exists(tag = precursor.protein_group_tag):
        raise HTTPException(status_code=404, detail=f"Protein group with tag {precursor.protein_group_tag} not found.")
    return DB.precursors.insert(protein_group_tag = precursor.protein_group_tag, peptide_sequence = precursor.sequence, charge = precursor.charge)


@router.post("/insert/bulk", summary="Bulk inserts a list of precursors into the database. Requires curator rights.")
def bulk_insert_precursors(precursors : List[PrecursorInsertModel], batch_size : int = 1000, transaction_batch_size : int = 400, user : UserModel = Depends(is_user_at_least_curator)) -> int:
    """
    Bulk inserts a list of precursors into the database. The precursor tags are derived from the
    peptide sequence and the charge state (sequence.charge). The precursors are connected
    to their respective protein groups. Precursors that already exist are merged.

    The input is chunked on the client side (batch_size) and each chunk is inserted using a
    CALL { ... } IN TRANSACTIONS subquery so that Neo4J commits the insert in smaller
    transactions (transaction_batch_size), avoiding memory errors for large inputs
    (e.g. 90K precursors per sample).

    Parameters
    ----------
    precursors : List[PrecursorInsertModel]
        The precursors to insert.
    batch_size : int, optional
        The number of precursors sent to the database per query, by default 1000
    transaction_batch_size : int, optional
        The number of rows per internal transaction (IN TRANSACTIONS OF ... ROWS), by default 400
    user : UserModel, optional
        The user that is extracted by the token, by default Depends(is_user_at_least_curator)

    Returns
    -------
    int
        The number of inserted precursors.

    Raises
    ------
    HTTPException
        If the request body is empty or the batch sizes are invalid.
    """
    if len(precursors) == 0:
        raise HTTPException(status_code=400, detail="No precursors provided.")
    if batch_size < 1:
        raise HTTPException(status_code=400, detail="batch_size must be at least 1.")
    if transaction_batch_size < 1:
        raise HTTPException(status_code=400, detail="transaction_batch_size must be at least 1.")
    return DB.precursors.bulk_insert(precursors = precursors, batch_size = batch_size, transaction_batch_size = transaction_batch_size)

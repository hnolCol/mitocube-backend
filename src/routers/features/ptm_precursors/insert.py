from fastapi import APIRouter, Depends, HTTPException
from lib.database.Database import get_db
from lib.database.abstract.Database import DatabaseABC
from typing import Dict, List
from config.models.user import UserModel
from config.models.ptm_precursors import PTMPrecursorInsertModel
from services.users import is_user_at_least_curator, get_user_from_token
from services.modifications import resolve_unimod


router = APIRouter(dependencies=[Depends(get_user_from_token)],
    prefix="/api/features/ptm_precursors",
    tags=["Features", "PTMPrecursors"]
)


def _resolve_modifications(precursor : PTMPrecursorInsertModel) -> None:
    for m in precursor.modifications:
        unimod = resolve_unimod(m.modification, residue = m.residue)
        m.unimod_id = unimod.accession
        m.unimod_name = unimod.name


@router.post("/insert", summary="Inserts a PTM precursor into the database. Requires curator rights.")
def insert_ptm_precursor(precursor : PTMPrecursorInsertModel, user : UserModel = Depends(is_user_at_least_curator), db : DatabaseABC = Depends(get_db)) -> bool:
    """
    Inserts a PTM precursor (a modified precursor, e.g. a phosphopeptide) into the database.
    The precursor tag is derived from the (modified) sequence and the charge state
    (sequence.charge), exactly like an unmodified precursor. The precursor is connected to the
    given protein groups and maps to one PTMSite per modification via [:MAPS_TO], so single- and
    multi-modified peptides (e.g. double phospho) are supported. Each modification string is
    resolved to a UniMod entry (accession, name or monoisotopic mass). Quantification is done at
    the precursor level via the regular precursor quantification endpoint.

    Parameters
    ----------
    precursor : PTMPrecursorInsertModel
        The PTM precursor to insert.
    user : UserModel, optional
        The user that is extracted by the token, by default Depends(is_user_at_least_curator)

    Returns
    -------
    bool
        True if the insertion was successful, False otherwise.

    Raises
    ------
    HTTPException
        If one of the protein groups with the given tags does not exist (404) or a modification
        cannot be resolved to a UniMod entry (400).
    """
    for protein_group_tag in precursor.protein_group_tags:
        if not db.protein_groups.exists(tag = protein_group_tag):
            raise HTTPException(status_code=404, detail=f"Protein group with tag {protein_group_tag} not found.")
    try:
        _resolve_modifications(precursor)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return db.precursors.insert_ptm_precursor(precursor = precursor)


@router.post("/insert/bulk", summary="Bulk inserts a list of PTM precursors into the database. Requires curator rights.")
def bulk_insert_ptm_precursors(precursors : List[PTMPrecursorInsertModel], batch_size : int = 1000, transaction_batch_size : int = 400, user : UserModel = Depends(is_user_at_least_curator), db : DatabaseABC = Depends(get_db)) -> Dict:
    """
    Bulk inserts a list of PTM precursors into the database, using the same chunking as the
    precursor bulk insert (CALL { ... } IN TRANSACTIONS). Each precursor maps to one PTMSite
    per modification via [:MAPS_TO]. Precursors whose protein groups do not exist are skipped
    and reported. Modification strings are resolved to UniMod entries.

    Parameters
    ----------
    precursors : List[PTMPrecursorInsertModel]
        The PTM precursors to insert.
    batch_size : int, optional
        The number of precursors sent to the database per query, by default 1000
    transaction_batch_size : int, optional
        The number of rows per internal transaction (IN TRANSACTIONS OF ... ROWS), by default 400
    user : UserModel, optional
        The user that is extracted by the token, by default Depends(is_user_at_least_curator)

    Returns
    -------
    Dict
        A report with the number of inserted precursors (valid) and the skipped precursors
        whose protein groups do not exist (not_found, not_found_tags).

    Raises
    ------
    HTTPException
        If the request body is empty, the batch sizes are invalid or a modification cannot be
        resolved to a UniMod entry.
    """
    if len(precursors) == 0:
        raise HTTPException(status_code=400, detail="No PTM precursors provided.")
    if batch_size < 1:
        raise HTTPException(status_code=400, detail="batch_size must be at least 1.")
    if transaction_batch_size < 1:
        raise HTTPException(status_code=400, detail="transaction_batch_size must be at least 1.")
    try:
        for precursor in precursors:
            _resolve_modifications(precursor)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return db.precursors.bulk_insert_ptm_precursors(precursors = precursors, batch_size = batch_size, transaction_batch_size = transaction_batch_size)

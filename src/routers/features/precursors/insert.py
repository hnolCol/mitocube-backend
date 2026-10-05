from fastapi import APIRouter, Depends, HTTPException
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

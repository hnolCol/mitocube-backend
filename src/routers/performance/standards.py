from fastapi import APIRouter, Depends, HTTPException
from typing import List
from config.models.user import UserModel
from config.models.performance import QCStandardInsertModel, QCStandardResponseModel, QCStandardType
from services.users import is_user_at_least_curator, get_user_from_token
from lib.database.Database import Database

DB = Database.DB()

router = APIRouter(dependencies=[Depends(get_user_from_token)],
    prefix="/api/standards",
    tags=["Performance", "QCStandards"])


@router.get("/types", summary="Returns the available QC standard types.")
def get_standard_types(user : UserModel = Depends(get_user_from_token)) -> List[str]:
    """
    Returns the available QC standard types (e.g. Cell lysate, Protein).
    """
    return [t.value for t in QCStandardType]


@router.get("", summary="Returns the QC standards. Requires at least curator rights.")
def get_standards(type : str = None, vendor : str = None, user : UserModel = Depends(is_user_at_least_curator)) -> List[QCStandardResponseModel]:
    """
    Returns the QC standards, optionally filtered by type and vendor.

    Parameters
    ----------
    type : str, optional
        The type of the standard (Cell lysate, Protein), by default None
    vendor : str, optional
        The vendor of the standard, by default None

    Returns
    -------
    List[QCStandardResponseModel]
        The QC standards.
    """
    if type is not None and type not in [t.value for t in QCStandardType]:
        raise HTTPException(status_code=400, detail=f"Unknown standard type {type}. Must be one of {[t.value for t in QCStandardType]}.")
    return DB.qc.get_standards(type = type, vendor = vendor)


@router.get("/{standard_tag}", summary="Returns a QC standard by its tag. Requires at least curator rights.")
def get_standard(standard_tag : str, user : UserModel = Depends(is_user_at_least_curator)) -> QCStandardResponseModel:
    """
    Returns a QC standard by its tag.

    Parameters
    ----------
    standard_tag : str
        The tag of the standard.

    Returns
    -------
    QCStandardResponseModel
        The standard.

    Raises
    ------
    HTTPException
        If the standard does not exist.
    """
    standards = [s for s in DB.qc.get_standards() if s.tag == standard_tag]
    if not standards: raise HTTPException(status_code=404, detail=f"QC standard with tag {standard_tag} not found.")
    return standards[0]


@router.post("/insert", summary="Inserts a QC standard. Requires at least curator rights.")
def insert_standard(standard : QCStandardInsertModel, user : UserModel = Depends(is_user_at_least_curator)) -> bool:
    """
    Inserts a QC standard into the database. Standards are immutable, an existing tag is merged.

    Parameters
    ----------
    standard : QCStandardInsertModel
        The standard to insert.
    user : UserModel, optional
        The user that is extracted by the token, by default Depends(is_user_at_least_curator)

    Returns
    -------
    bool
        True if the standard was inserted.
    """
    return DB.qc.insert_standard(standard = standard)


@router.delete("/{standard_tag}", summary="Deletes a QC standard. Requires at least curator rights.")
def delete_standard(standard_tag : str, user : UserModel = Depends(is_user_at_least_curator)) -> bool:
    """
    Deletes a QC standard. A standard can only be deleted if no QC run is linked to it.

    Parameters
    ----------
    standard_tag : str
        The tag of the standard to delete.
    user : UserModel, optional
        The user that is extracted by the token, by default Depends(is_user_at_least_curator)

    Returns
    -------
    bool
        True if the standard was deleted.

    Raises
    ------
    HTTPException
        If the standard does not exist (404) or is still linked to QC runs (409).
    """
    if not DB.qc.standard_exists(tag = standard_tag): raise HTTPException(status_code=404, detail=f"QC standard with tag {standard_tag} not found.")
    if not DB.qc.delete_standard(tag = standard_tag): raise HTTPException(status_code=409, detail=f"QC standard with tag {standard_tag} is still linked to QC runs and cannot be deleted.")
    return True

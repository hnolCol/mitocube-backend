from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict

from lib.database.Database import get_db
from lib.database.abstract.Database import DatabaseABC
from config.models.user import UserModel
from config.models.plates import PlateInsertModel, PlateModel, PlateOptionsModel
from services.users import get_user_from_token, is_user_at_least_curator


router = APIRouter(dependencies=[Depends(get_user_from_token)],
    prefix="/api",
    tags=["Plates"],
    )

@router.get("/plates/options", response_model=PlateOptionsModel)
def get_plate_options(user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)):
    "Returns the selectable formats, cold storages, plate types and vendors for creating a plate."
    return db.plates.get_options()

@router.get("/plates", response_model=List[PlateModel])
def get_plates(user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)):
    "Returns all plates."
    return db.plates.list()


@router.get("/plates/next-name")
def get_next_plate_name(rows : int, columns : int, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> Dict[str, str]:
    "Suggests the next free plate name for a format, e.g. P-96-004."
    return {"name": db.plates.next_name(rows=rows, columns=columns)}


@router.post("/plates", response_model=PlateModel)
def create_plate(plate : PlateInsertModel, user : UserModel = Depends(is_user_at_least_curator), db : DatabaseABC = Depends(get_db)):
    "Creates a new plate. The user must be at least curator."
    try:
        tag = db.plates.insert(plate=plate, user_tag=user.tag)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return db.plates.get(tag=tag)


@router.get("/plates/{plate_tag}", response_model=PlateModel)
def get_plate(plate_tag : str, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)):
    "Returns a plate by its tag."
    plate = db.plates.get(tag=plate_tag)
    if plate is None:
        raise HTTPException(status_code=404, detail="Plate not found.")
    return plate


@router.delete("/plates/{plate_tag}")
def delete_plate(plate_tag : str, user : UserModel = Depends(is_user_at_least_curator), db : DatabaseABC = Depends(get_db)) -> bool:
    "Deletes a plate. Not possible if runs are stored on it."
    if not db.plates.exists(tag=plate_tag):
        raise HTTPException(status_code=404, detail="Plate not found.")
    try:
        return db.plates.delete(tag=plate_tag)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    
@router.get("/plates/{plate_tag}/occupied")
def get_plate_occupied_wells(plate_tag : str, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> List[Dict]:
    "Returns the wells of a plate that already hold a run."
    if not db.plates.exists(tag=plate_tag):
        raise HTTPException(status_code=404, detail="Plate not found.")
    return [{"row_index": r, "column_index": c, "position": label}
            for r, c, label in db.plates.get_occupied_positions(tag=plate_tag)]
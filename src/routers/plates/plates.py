from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict

from lib.database.Database import get_db
from lib.database.abstract.Database import DatabaseABC
from config.enums.users.roles import UserRolesEnum
from config.models.user import UserModel
from config.models.plates import PlateInsertModel, PlateModel, PlateOptionsModel, PlateRunlistModel, PlateSubmissionModel, PlateSubmissionsLayoutModel
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
    "Returns all plates. Runlist and submission counts are only visible to curators."
    plates = db.plates.list()
    if user.role < UserRolesEnum.CURATOR:
        for plate in plates:
            plate.n_runlists = 0
            plate.n_submissions = 0
    return plates


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
    "Returns a plate by its tag. Runlist and submission counts are only visible to curators."
    plate = db.plates.get(tag=plate_tag)
    if plate is None:
        raise HTTPException(status_code=404, detail="Plate not found.")
    if user.role < UserRolesEnum.CURATOR:
        plate.n_runlists = 0
        plate.n_submissions = 0
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
    
@router.get("/plates/{plate_tag}/runlists", response_model=List[PlateRunlistModel])
def get_plate_runlists(plate_tag : str, user : UserModel = Depends(is_user_at_least_curator), db : DatabaseABC = Depends(get_db)) -> List[PlateRunlistModel]:
    "Returns all runlists that have at least one run on the plate. Only visible to curators."
    if not db.plates.exists(tag=plate_tag):
        raise HTTPException(status_code=404, detail="Plate not found.")
    return db.plates.get_runlists(tag=plate_tag)


@router.get("/plates/{plate_tag}/submissions", response_model=List[PlateSubmissionModel])
def get_plate_submissions(plate_tag : str, user : UserModel = Depends(is_user_at_least_curator), db : DatabaseABC = Depends(get_db)) -> List[PlateSubmissionModel]:
    "Returns the distinct submissions that were measured on the plate via any runlist. Only visible to curators."
    if not db.plates.exists(tag=plate_tag):
        raise HTTPException(status_code=404, detail="Plate not found.")
    return db.plates.get_submissions(tag=plate_tag)


@router.get("/plates/{plate_tag}/submissions-layout", response_model=PlateSubmissionsLayoutModel)
def get_plate_submissions_layout(plate_tag : str, user : UserModel = Depends(is_user_at_least_curator), db : DatabaseABC = Depends(get_db)) -> PlateSubmissionsLayoutModel:
    "Returns the full well grid of the plate with the well -> submission mapping and the submission legend. Only visible to curators."
    if not db.plates.exists(tag=plate_tag):
        raise HTTPException(status_code=404, detail="Plate not found.")
    layout = db.plates.get_submission_layout(tag=plate_tag)
    if layout is None:
        raise HTTPException(status_code=404, detail="Plate not found.")
    return layout


@router.get("/plates/{plate_tag}/occupied")
def get_plate_occupied_wells(plate_tag : str, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> List[Dict]:
    "Returns the wells of a plate that already hold a run."
    if not db.plates.exists(tag=plate_tag):
        raise HTTPException(status_code=404, detail="Plate not found.")
    return [{"row_index": r, "column_index": c, "position": label}
            for r, c, label in db.plates.get_occupied_positions(tag=plate_tag)]
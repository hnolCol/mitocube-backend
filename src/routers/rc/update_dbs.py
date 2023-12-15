from fastapi import APIRouter, Depends, BackgroundTasks

from services.users import is_user_admin

from lib.data.annotations.ABCAnnotations import PandaFeatureDatabase, AnnotationDatabase
from lib.data.database.ABCDatabase import MCAttributes, MCDatabase

from config.models.user import User

router = APIRouter(
    prefix="/api/rc",
    tags=["Dataset"]
    )



@router.get("/clear/db-cache",  # , response_model=PlayModel)
            summary="Empties the dataset cache of the database which will force access to the database for a following request.")
def update_features(background_task : BackgroundTasks, user : User = Depends(is_user_admin)):
    """Empties the cache of the database. New requests for dataset will be loaded directly from the db."""
    db = MCDatabase.getDatabase()
    db.clearCachedDatasets()


@router.get("/update/annotations",  # , response_model=PlayModel)
            summary="Triggers an update for the annotation database.")
def update_annotations(background_task : BackgroundTasks, user : User = Depends(is_user_admin)):
    """Triggers an update for the annotation database."""
    db_annotations = AnnotationDatabase()
    db_annotations.update()

@router.get("/update/attributes",  # , response_model=PlayModel)
            summary="Triggers an update for the attribute configuration database.")
def update_attributes(background_task : BackgroundTasks, user : User = Depends(is_user_admin)):
    """Triggers an update for the attribute configuration database."""
    db_attributes = MCAttributes.getAttributeDatabase()
    db_attributes.update()

@router.get("/update/features",  # , response_model=PlayModel)
            summary="Triggers an update for the feature database.")
def update_features(background_task : BackgroundTasks, user : User = Depends(is_user_admin)):
    """Triggers an update for the feature database."""
    db_features = PandaFeatureDatabase()
    db_features.update()

from fastapi import APIRouter, Depends, HTTPException
from collections import OrderedDict
from typing import List 

from lib.database.Database import Database

from config.models.annotations.annotations import ( AnnotationGroupModel, AnnotationModel)

from lib.database.neo4j.Annotations import ( Neo4JAnnotationGroup,  Neo4JAnnotation)
from config.exceptions.HTTPExceptions import no_data_found_http_exception
from config.models.user import UserModel
from config.models.parameter import APIParamString
from services.users import get_user_from_token, is_user_admin

DB = Database.DB()

router = APIRouter(
    prefix="api/annotationgroups/annotations",
    tags=["Annotations"],
)

@router.get("/q")
def find_annotations_in_group( annotation_group_tag : str, tag : str) -> List[str]:
    """Finds annotations in an annotation group."""

    tags = DB.annotation_groups.get_annotations(annotation_group_tag= annotation_group_tag, tag= tag)
    return tags

@router.get("/{annotation_group_tag}/annotations/{tag}")
def get_annotation_in_group( annotation_group_tag : str, tag : str) -> AnnotationModel:
    """Get annotation by its tag."""

    if not DB.annotation_groups.exists(annotation_group_tag):
        raise HTTPException(status_code=404, details="Annotation group not found.")
    
    annotation= DB.annotations.get(annotation_group_tag= annotation_group_tag, tag= tag)
    return annotation

@router.post("/{annotation_group_tag}/annotations")
def insert_annotation(annotation_group_tag : str, annotation : AnnotationModel, user: UserModel = Depends(is_user_admin)) -> bool:
    """Inserts a new annotation in an annotation group."""

    if not DB.annotation_groups.exists(annotation_group_tag):
        raise HTTPException(status_code=404, details="Annotation group not found.")
    
    ok = DB.annotations.insert(nnotation_group_tag= annotation_group_tag, annotation= annotation)
    if not ok:
        raise HTTPException(status_code=500, details="Failed to insert annotation.")
    return ok

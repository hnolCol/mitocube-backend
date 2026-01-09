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
    prefix="api/annotationgroups",
    tags=["Annotations"],
)

@router.get("/q")
def find_annotationn_group( tag : str) -> List[AnnotationGroupModel]:
    """Finds annotation groups by its tag."""

    tags = DB.annotation_groups.find(tag= tag)
    return tags 

@router.get("/{tag}")
def get_annotation_group( tag : str) -> AnnotationGroupModel:
    """Get annotation group by its tag."""

    if not DB.annotation_groups.exists(tag):
        raise HTTPException(status_code=404, details="Annotation Group not found.")
    
    annotation_group= DB.annotation_groups.get(tag= tag)
    return annotation_group

@router.post("/")
def insert_annotation_group( annotation_group : AnnotationGroupModel, user: UserModel = Depends(is_user_admin)) -> bool:
    """Insert a new annotation group."""
    
    ok = DB.annotation_groups.insert(annotation_group= annotation_group)
    if not ok:
        raise HTTPException(status_code=500, details="Could not insert annotationn group.")
    
    return ok

@router.get("/{annotation_group_tag}/annotations")
def get_annotations_in_group( annotation_group_tag : str) -> List[str]:
    """Get annotation tags in the annotation group."""

    if not DB.annotation_groups.exists(annotation_group_tag):
        raise HTTPException(status_code=404, details="Annptation group not found.")

    annotation_tags = DB.annotation_groups.get_annotations(annotation_group_tag= annotation_group_tag)
    return annotation_tags


from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional

from lib.database.Database import Database

from config.models.annotations.annotations import ( AnnotationGroupsModel, AnnotationsModel)
from lib.database.neo4j.Annotations import ( Neo4JAnnotationGroups,  Neo4JAnnotations)

from config.models.user import UserModel
from services.users import get_user_from_token, is_user_admin

DB = Database.DB()

router = APIRouter(
    prefix="/api/annotations",
    tags=["Annotations"],
)

@router.get("/q", response_model=List[str])
def find_annotations(search_string: Optional[str] = None, group_tag: Optional[str] = None, protein_tag: Optional[str] = None, user: UserModel = Depends(get_user_from_token),):
    
    tags = DB.annotations.find(search_string=search_string, group_tag=group_tag, protein_tag=protein_tag)
    return tags



@router.get("/{tag}", response_model=AnnotationsModel)
def get_annotation(tag: str):
    
    if not DB.annotations.exists(tag):
        raise HTTPException(status_code=404, detail="Annotation not found")
    
    annotation= DB.annotations.get(tag= tag)
    return annotation

@router.post("/", response_model=bool)
def insert_annotation( annotation: AnnotationsModel, user: UserModel = Depends(is_user_admin)):

    ok = DB.annotations.insert(annotation = annotation)
    if not ok:
        raise HTTPException(status_code=500, detail="Could not insert annotation.")
    
    return ok

@router.get("/{tag}/proteins/count", response_model=int)
def get_annotation_protein_count( tag: str):

    if not DB.annotations.exists(tag):
        raise HTTPException( status_code=404, detail="Annotation not found")
    print(DB.annotations.count_proteins(tag))
    return DB.annotations.count_proteins(tag)

@router.get("/groups/q", response_model=List[str])
def find_annotation_groups(search_string: Optional[str] = None, protein_tag: Optional[str] = None):
    return DB.annotation_groups.find(
        search_string=search_string,
        protein_tag=protein_tag,
    )


@router.get("/groups/{group_tag}", response_model=AnnotationGroupsModel)
def get_annotation_group(group_tag: str, user: UserModel = Depends(get_user_from_token)):
    if not DB.annotation_groups.exists(group_tag):
        raise HTTPException(status_code=404, detail="Annotation group not found")

    return DB.annotation_groups.get(tag=group_tag)

@router.get("/groups/{group_tag}/annotations", response_model=List[str])
def get_annotations_in_group(group_tag: str, user: UserModel = Depends(get_user_from_token)):
    
    if not DB.annotation_groups.exists(group_tag):
        raise HTTPException(status_code=404, detail="Annotation group not found")

    return DB.annotation_groups.get_annotations(group_tag)

@router.post("/groups/", response_model=bool)
def insert_annotation_group( annotation_group: AnnotationGroupsModel, user: UserModel = Depends(is_user_admin)):
    print(DB.annotation_groups.insert(annotation_group))
    ok = DB.annotation_groups.insert(annotation_group)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to insert annotation group")

    return ok

@router.get("/groups/{group_tag}/annotations/count", response_model=int)
def get_annotation_in_group_count( group_tag: str, user: UserModel = Depends(get_user_from_token),):
    
    if not DB.annotation_groups.exists(group_tag):
        raise HTTPException( status_code=404, detail="Annotation group not found")

    return DB.annotation_groups.count_annotations(group_tag)


@router.put("/groups/{group_tag}/annotations/{tag}", response_model=bool)
def update_annotation( group_tag: str, tag: str, annotation: AnnotationsModel, user: UserModel = Depends(is_user_admin)):
    
    if not DB.annotations.exists(tag):
        raise HTTPException(status_code=404, detail="Annotation not found")
    
    ok = DB.annotations.update( group_tag=group_tag,
                                annotation_tag=tag,
                                annotation=annotation,
                            )
    
    if not ok:
        raise HTTPException(status_code=500, detail="Could not update annotation.")
    
    return ok
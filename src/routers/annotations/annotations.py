from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional, Dict, Set
from scipy.stats import fisher_exact

from lib.database.Database import Database

from config.models.annotations.annotations import ( AnnotationGroupsInsertModel, AnnotationGroupsModel, AnnotationsModel)
from lib.database.neo4j.Annotations import ( Neo4JAnnotationGroups,  Neo4JAnnotations)

from config.models.user import UserModel
from services.users import get_user_from_token, is_user_admin
from services.encryption import create_hierarchical_hash
from setup_utils.annotations_from_url.update_annotations import update_annotations_from_group_url
from config.models.parameter import APIParamString
import numpy as np
DB = Database.DB()

router = APIRouter(
    prefix="/api/annotations",
    tags=["Annotations"],
)

@router.get("/q", response_model=List[str]|List[Dict])
def find_annotations(search_string: Optional[str] = None, group_tags: Optional[str] = None, protein_tags: Optional[str] = None, limit : int = None, group_by_group: bool = False, user: UserModel = Depends(get_user_from_token)):
    "Finds annotations matching the search criteria."
    #TODO add submission tags here  and in find only return if protein is quantified in submission and in that annotation group.
    tags = DB.annotations.find(search_string=search_string, 
                               group_tags=APIParamString(param = group_tags).param,  #transforms string with semicolon into list
                               protein_tags=APIParamString(param = protein_tags).param,  #transforms string with semicolon into list
                               limit=limit, 
                               group_by_group=group_by_group)
    return tags


@router.get("/{tag}", response_model=AnnotationsModel)
def get_annotation(tag: str):
    
    if not DB.annotations.exists(tag):
        raise HTTPException(status_code=404, detail="Annotation not found")
    
    annotation= DB.annotations.get(tag= tag)
    return annotation

@router.get("/{tag}/annotates/{protein_tag}", response_model=bool)
def is_protein_annotated_with(tag: str, protein_tag: str):
    if not DB.annotations.exists(tag):
        raise HTTPException(status_code=404, detail="Annotation not found")
    if ";" in protein_tag: #handle protein groups 
        protein_tags = APIParamString(param=protein_tag).param
        
    else: 
        protein_tags = [protein_tag]
    boolIdx = DB.annotations.isin(tag = tag, protein_tags = protein_tags)
    return np.any(boolIdx.values) if len(boolIdx) > 0 else False


@router.get("/{tag}/annotates", response_model=List[Dict])
def are_proteins_annotated_with(tag: str, protein_tags: str):
    if not DB.annotations.exists(tag):
        raise HTTPException(status_code=404, detail="Annotation not found")
    
    protein_tags = APIParamString(param=protein_tags).param
    
    for pt in protein_tags:
        if not DB.proteins.exists(pt):
            raise HTTPException(status_code=404, detail=f"Protein {pt} not found")
    boolIdcs = DB.annotations.isin(tag = tag, protein_tags = protein_tags)
    return [{"protein_tag": protein_tag, "isin": boolIdcs[protein_tag], "annotation_tag" : tag}  for protein_tag in boolIdcs.index]


@router.post("/", response_model=bool)
def insert_annotation( annotation: AnnotationsModel, user: UserModel = Depends(get_user_from_token)):

    ok = DB.annotations.insert(annotation = annotation)
    if not ok:
        raise HTTPException(status_code=500, detail="Could not insert annotation.")
    
    return ok

@router.get("/{tag}/proteins/count", response_model=int)
def get_annotation_protein_count( tag: str):

    if not DB.annotations.exists(tag):
        raise HTTPException( status_code=404, detail="Annotation not found")
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
def get_annotations_in_group(group_tag: str, limit: int = 20, user: UserModel = Depends(get_user_from_token)):
    
    if not DB.annotation_groups.exists(group_tag):
        raise HTTPException(status_code=404, detail="Annotation group not found")

    return DB.annotation_groups.get_annotations(group_tag, limit=limit)

@router.post("/groups/", response_model=bool)
def insert_annotation_group( annotation_group: AnnotationGroupsInsertModel, user: UserModel = Depends(get_user_from_token)):
    tag = create_hierarchical_hash(annotation_group.model_dump(exclude_none=True))
    annotation_group_with_tag = AnnotationGroupsModel(**annotation_group.model_dump(exclude_none=True), tag=tag)
    ok = DB.annotation_groups.insert(annotation_group_with_tag, user_tag=user.tag)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to insert annotation group")

    return ok

@router.get("/groups/{group_tag}/annotations/count", response_model=int)
def get_annotation_in_group_count( group_tag: str, user: UserModel = Depends(get_user_from_token),):
    
    if not DB.annotation_groups.exists(group_tag):
        raise HTTPException( status_code=404, detail="Annotation group not found")

    return DB.annotation_groups.count_annotations(group_tag)


@router.put("/{tag}", response_model=bool)
def update_annotation(annotation: AnnotationsModel, user: UserModel = Depends(get_user_from_token)):
    
    ok = DB.annotations.update_annotation( annotation=annotation, user_tag=user.tag)
    
    if not ok:
        raise HTTPException(status_code=500, detail="Could not update annotation.")
    
    return ok


@router.delete("/{tag}", response_model=bool)
def delete_annotation(tag: str, user: UserModel = Depends(get_user_from_token)):
    
    if not DB.annotations.exists(tag):
        raise HTTPException(status_code=404, detail="Annotation not found")
    
    ok = DB.annotations.delete_annotation(tag)
    
    if not ok:
        raise HTTPException(status_code=500, detail="Could not delete annotation.")
    
    return ok





@router.post("/groups/{group_tag}/update", response_model=bool)
def update_annotation_group_from_url(group_tag: str, user: UserModel = Depends(is_user_admin)):
    
    if not DB.annotation_groups.exists(group_tag):
        raise HTTPException(status_code=404, detail="Annotation group not found")

    group = DB.annotation_groups.get(group_tag)

    if not group.url:
        raise HTTPException( status_code=400, detail="Annotation group has no URL")

    update_annotations_from_group_url(group=group,annotations_db=DB.annotations)

    return True

@router.put("/groups/{group_tag}", response_model=bool)
def edit_annotation_group(annotationgroup: AnnotationGroupsModel, user: UserModel = Depends(is_user_admin)):
    
    ok = DB.annotation_groups.edit_annotation_group(annotationgroup=annotationgroup, user_tag=user.tag)

    if not ok:
        raise HTTPException(status_code=500, detail="Could not update annotation group.")
    
    return ok

@router.get("/{tag}/proteins", response_model=List[str])
def get_proteins_for_annotation( tag: str, submission_tag: Optional[str] = None,  user: UserModel = Depends(get_user_from_token)):
    """Get protein tags for annotation, optionally filtered by submission."""
    
    if not DB.annotations.exists(tag):
        raise HTTPException(status_code=404, detail="Annotation not found")
    
    protein_tags = DB.annotations.get_protein_tags(tag, submission_tag)
    
    return protein_tags

@router.get("/analysis/fisher", response_model=List[Dict])
def fisher_annotation_analysis(
    submission_tag: str = Query(..., description="Submission tag to analyze"),
    target_proteins: List[str] = Query(..., description="List of target protein tags"),
    group_tag: str = Query(..., description="Annotation group tag to analyze"),
) -> List[Dict]:
    
    # Get all proteins in submission
    all_proteins = set(DB.submissions.get_proteins_in_submission(submission_tag))
    
    if not all_proteins:
        raise HTTPException(status_code=404, detail="No proteins in submission.")
    
    # Split into target and general
    target = set(target_proteins) & all_proteins
    general = all_proteins - target
    
    if not target:
        raise HTTPException(status_code=400, detail="No valid target proteins.")
    
    # Get annotations filtered by submission
    annotation_to_proteins = DB.annotations.get_proteins_by_annotation_group(
        group_tag=group_tag,
        submission_tag=submission_tag
    )

    results = []
    
    for annotation_tag, annotated_proteins in annotation_to_proteins.items():
        annotated_set = set(annotated_proteins)
    

        # Build 2x2 table
        a = len(target & annotated_set)
        b = len(target) - a
        c = len(general & annotated_set)
        d = len(general) - c
        
        odds_ratio, p_value = fisher_exact([[a, b], [c, d]], alternative="greater")
        
        results.append({
            "annotation_tag": annotation_tag,
            "target_with_annotation": a,
            "target_total": len(target),
            "general_with_annotation": c,
            "general_total": len(general),
            "odds_ratio": float(odds_ratio),
            "p_value": float(p_value),
        })
    
    results.sort(key=lambda x: x["p_value"])
    return results
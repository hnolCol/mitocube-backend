from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional, Dict
from scipy.stats import fisher_exact

from lib.database.Database import get_db
from lib.database.abstract.Database import DatabaseABC

from config.models.annotations.annotations import ( AnnotationGroupsInsertModel, AnnotationGroupsModel, AnnotationsModel)
from lib.database.neo4j.Annotations import ( Neo4JAnnotationGroups,  Neo4JAnnotations)

from config.models.user import UserModel
from services.users import get_user_from_token, is_user_admin
from services.submission import check_submission_access, check_submission_tags_access
from services.encryption import create_hierarchical_hash
from setup_utils.annotations_from_url.update_annotations import update_annotations_from_group_url
from config.models.parameter import APIParamString
from services.annotations.enrichment import compute_annotation_enrichment, enrichment_records
import numpy as np

router = APIRouter(dependencies=[Depends(get_user_from_token)],
    prefix="/api/annotations",
    tags=["Annotations"],
)

@router.get("/q", response_model=List[str]|List[Dict])
def find_annotations(search_string: Optional[str] = None, group_tags: Optional[str] = None, protein_tags: Optional[str] = None, limit : int = None, group_by_group: bool = False, submission_tags: Optional[str] = None, user: UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)):
    "Finds annotations matching the search criteria."
    check_submission_tags_access(submission_tags = submission_tags, user = user, db = db)
    #TODO add submission tags here  and in find only return if protein is quantified in submission and in that annotation group.
    tags = db.annotations.find(search_string=search_string, 
                               group_tags=APIParamString(param = group_tags).param,  #transforms string with semicolon into list
                               protein_tags=APIParamString(param = protein_tags).param,  #transforms string with semicolon into list
                               submission_tags=APIParamString(param = submission_tags).param,  #transforms string with semicolon into list
                               limit=limit, 
                               group_by_group=group_by_group)
    return tags


@router.get("/{tag}", response_model=AnnotationsModel)
def get_annotation(tag: str, db : DatabaseABC = Depends(get_db)):
    
    if not db.annotations.exists(tag):
        raise HTTPException(status_code=404, detail="Annotation not found")
    
    annotation= db.annotations.get(tag= tag)
    return annotation

@router.get("/{tag}/annotates/{protein_tag}", response_model=bool)
def is_protein_annotated_with(tag: str, protein_tag: str, db : DatabaseABC = Depends(get_db)):
    if not db.annotations.exists(tag):
        raise HTTPException(status_code=404, detail="Annotation not found")
    if ";" in protein_tag: #handle protein groups 
        protein_tags = APIParamString(param=protein_tag).param
        
    else: 
        protein_tags = [protein_tag]
    boolIdx = db.annotations.isin(tag = tag, protein_tags = protein_tags)
    return np.any(boolIdx.values) if len(boolIdx) > 0 else False


@router.get("/{tag}/annotates", response_model=List[Dict])
def are_proteins_annotated_with(tag: str, protein_tags: str, db : DatabaseABC = Depends(get_db)):
    if not db.annotations.exists(tag):
        raise HTTPException(status_code=404, detail="Annotation not found")
    
    protein_tags = APIParamString(param=protein_tags).param
    
    for pt in protein_tags:
        if not db.proteins.exists(pt):
            raise HTTPException(status_code=404, detail=f"Protein {pt} not found")
    boolIdcs = db.annotations.isin(tag = tag, protein_tags = protein_tags)
    return [{"protein_tag": protein_tag, "isin": boolIdcs[protein_tag], "annotation_tag" : tag}  for protein_tag in boolIdcs.index]


@router.post("/", response_model=bool)
def insert_annotation( annotation: AnnotationsModel, user: UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)):

    ok = db.annotations.insert(annotation = annotation)
    if not ok:
        raise HTTPException(status_code=500, detail="Could not insert annotation.")
    
    return ok

@router.get("/{tag}/proteins/count", response_model=int)
def get_annotation_protein_count( tag: str, db : DatabaseABC = Depends(get_db)):

    if not db.annotations.exists(tag):
        raise HTTPException( status_code=404, detail="Annotation not found")
    return db.annotations.count_proteins(tag)

@router.get("/groups/q", response_model=List[str])
def find_annotation_groups(search_string: Optional[str] = None, protein_tag: Optional[str] = None, db : DatabaseABC = Depends(get_db)):
    return db.annotation_groups.find(
        search_string=search_string,
        protein_tag=protein_tag,
    )


@router.get("/groups/{group_tag}", response_model=AnnotationGroupsModel)
def get_annotation_group(group_tag: str, user: UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)):
    if not db.annotation_groups.exists(group_tag):
        raise HTTPException(status_code=404, detail="Annotation group not found")

    return db.annotation_groups.get(tag=group_tag)


@router.get("/groups/{group_tag}/annotations", response_model=List[str])
def get_annotations_in_group(group_tag: str, limit: int = 20, user: UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)):
    
    if not db.annotation_groups.exists(group_tag):
        raise HTTPException(status_code=404, detail="Annotation group not found")

    return db.annotation_groups.get_annotations(group_tag, limit=limit)

@router.post("/groups/", response_model=bool)
def insert_annotation_group( annotation_group: AnnotationGroupsInsertModel, user: UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)):
    tag = create_hierarchical_hash(annotation_group.model_dump(exclude_none=True))
    annotation_group_with_tag = AnnotationGroupsModel(**annotation_group.model_dump(exclude_none=True), tag=tag)
    ok = db.annotation_groups.insert(annotation_group_with_tag, user_tag=user.tag)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to insert annotation group")

    return ok

@router.get("/groups/{group_tag}/annotations/count", response_model=int)
def get_annotation_in_group_count( group_tag: str, user: UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)):
    
    if not db.annotation_groups.exists(group_tag):
        raise HTTPException( status_code=404, detail="Annotation group not found")

    return db.annotation_groups.count_annotations(group_tag)


@router.put("/{tag}", response_model=bool)
def update_annotation(annotation: AnnotationsModel, user: UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)):
    
    ok = db.annotations.update_annotation( annotation=annotation, user_tag=user.tag)
    
    if not ok:
        raise HTTPException(status_code=500, detail="Could not update annotation.")
    
    return ok


@router.delete("/{tag}", response_model=bool)
def delete_annotation(tag: str, user: UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)):
    
    if not db.annotations.exists(tag):
        raise HTTPException(status_code=404, detail="Annotation not found")
    
    ok = db.annotations.delete_annotation(tag)
    
    if not ok:
        raise HTTPException(status_code=500, detail="Could not delete annotation.")
    
    return ok





@router.post("/groups/{group_tag}/update", response_model=bool)
def update_annotation_group_from_url(group_tag: str, user: UserModel = Depends(is_user_admin), db : DatabaseABC = Depends(get_db)):
    
    if not db.annotation_groups.exists(group_tag):
        raise HTTPException(status_code=404, detail="Annotation group not found")

    group = db.annotation_groups.get(group_tag)

    if not group.url:
        raise HTTPException( status_code=400, detail="Annotation group has no URL")

    update_annotations_from_group_url(group=group,annotations_db=db.annotations)

    return True

@router.put("/groups/{group_tag}", response_model=bool)
def edit_annotation_group(annotationgroup: AnnotationGroupsModel, user: UserModel = Depends(is_user_admin), db : DatabaseABC = Depends(get_db)):
    
    ok = db.annotation_groups.edit_annotation_group(annotationgroup=annotationgroup, user_tag=user.tag)

    if not ok:
        raise HTTPException(status_code=500, detail="Could not update annotation group.")
    
    return ok

@router.get("/{tag}/proteins", response_model=List[str])
def get_proteins_for_annotation( tag: str, submission_tag: Optional[str] = None,  user: UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)):
    """Get protein tags for annotation, optionally filtered by submission."""
    
    if not db.annotations.exists(tag):
        raise HTTPException(status_code=404, detail="Annotation not found")
    
    if submission_tag is not None:
        check_submission_access(submission_tag = submission_tag, user = user, db = db)
    protein_tags = db.annotations.get_protein_tags(tag, submission_tag)
    
    return protein_tags

@router.get("/analysis/fisher", response_model=List[Dict])
def fisher_annotation_analysis(
    submission_tag: str = Query(..., description="Submission tag to analyze"),
    target_proteins: List[str] = Query(..., description="List of target protein tags"),
    group_tag: str = Query(..., description="Annotation group tag to analyze"),
    user : UserModel = Depends(get_user_from_token),
    db : DatabaseABC = Depends(get_db),
) -> List[Dict]:

    check_submission_access(submission_tag = submission_tag, user = user, db = db)
    
    # Get all proteins in submission
    all_proteins = set(db.submissions.get_proteins_in_submission(submission_tag))
    
    if not all_proteins:
        raise HTTPException(status_code=404, detail="No proteins in submission.")
    
    # Split into target and general
    target = set(target_proteins) & all_proteins
    general = all_proteins - target
    
    if not target:
        raise HTTPException(status_code=400, detail="No valid target proteins.")
    
    # Get annotations filtered by submission
    annotation_to_proteins = db.annotations.get_proteins_by_annotation_group(
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


@router.get("/analysis/enrichment", response_model=List[Dict])
def annotation_enrichment_analysis(
    target_proteins: str = Query(..., description="Semicolon-separated protein tags defining the target list to test for enrichment."),
    submission_tags: Optional[str] = Query(None, description="Semicolon-separated submission tags. The background universe is the union of the proteins quantified in these submissions. The user needs access to all of them."),
    proteome_tag: Optional[str] = Query(None, description="Proteome tag. The background universe is all proteins of this proteome. Provide either submission_tags or proteome_tag, not both."),
    group_tag: Optional[str] = Query(None, description="Restrict the tested annotations to this annotation group."),
    search_string: Optional[str] = Query(None, description="Only test annotations whose text or tag contains this string (case-insensitive)."),
    min_overlap: int = Query(1, ge=1, description="Minimum number of target proteins annotated for an annotation to be tested."),
    limit: Optional[int] = Query(None, ge=1, description="Maximum number of results (after sorting by p-value)."),
    user: UserModel = Depends(get_user_from_token),
    db: DatabaseABC = Depends(get_db),
) -> List[Dict]:
    """Enrichment analysis of annotations for a defined target protein list.

    For every annotation (optionally restricted to a group / search string) a
    one-sided Fisher exact test (alternative="greater") on the 2x2 table of
    target list vs. background universe is computed, and p-values are corrected
    with Benjamini-Hochberg FDR. The universe is either the union of the
    proteins quantified in the given submissions (submission-wide volcano
    plots) or all proteins of a proteome (cross-submission comparisons of the
    same proteome).
    """
    target = APIParamString(param=target_proteins).param or []
    if len(target) == 0:
        raise HTTPException(status_code=400, detail="No target proteins provided.")

    if submission_tags is not None and proteome_tag is not None:
        raise HTTPException(status_code=400, detail="Provide either submission_tags or proteome_tag, not both.")

    if submission_tags is not None:
        tags = APIParamString(param=submission_tags).param or []
        if len(tags) == 0:
            raise HTTPException(status_code=400, detail="submission_tags is empty.")
        check_submission_tags_access(submission_tags=tags, user=user, db=db)
        universe = set()
        for tag in tags:
            universe.update(db.submissions.get_proteins_in_submission(tag))
        universe = sorted(universe)
    elif proteome_tag is not None:
        universe = db.proteins.get_protein_tags_by_proteome(proteome_tag)
    else:
        raise HTTPException(status_code=400, detail="Either submission_tags or proteome_tag must be provided to define the background universe.")

    if len(universe) == 0:
        raise HTTPException(status_code=404, detail="No proteins found in the background universe.")

    universe_set = set(universe)
    target_in_universe = [t for t in dict.fromkeys(target) if t in universe_set]
    if len(target_in_universe) == 0:
        raise HTTPException(status_code=400, detail="No target proteins are part of the background universe.")

    overlap_counts = db.annotations.get_annotation_overlap_counts(
        universe_proteins=universe,
        target_proteins=target_in_universe,
        group_tag=group_tag,
    )

    if search_string is not None and len(search_string) > 0 and not overlap_counts.empty:
        needle = search_string.lower()
        mask = overlap_counts["annotation_tag"].str.lower().str.contains(needle) | overlap_counts["text"].fillna("").str.lower().str.contains(needle)
        overlap_counts = overlap_counts[mask]

    result = compute_annotation_enrichment(
        overlap_counts=overlap_counts,
        target_size=len(target_in_universe),
        universe_size=len(universe),
        min_overlap=min_overlap,
    )
    return enrichment_records(result, limit=limit)
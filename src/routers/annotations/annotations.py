from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional, Dict
from scipy.stats import fisher_exact

from lib.database.Database import get_db
from lib.database.abstract.Database import DatabaseABC

from config.models.annotations.annotations import ( AnnotationGroupsInsertModel, AnnotationGroupsModel, AnnotationsModel, AnnotationShiftRequestModel )
from lib.database.neo4j.Annotations import ( Neo4JAnnotationGroups,  Neo4JAnnotations)

from config.models.user import UserModel
from services.users import get_user_from_token, is_user_admin
from services.submission import check_submission_access, check_submission_tags_access
from services.encryption import create_hierarchical_hash
from setup_utils.annotations_from_url.update_annotations import update_annotations_from_group_url
from config.models.parameter import APIParamString
from services.annotations.enrichment import compute_annotation_enrichment, compute_annotation_shift_from_member_values, enrichment_records
from services.annotations.gsea import ( compute_annotation_gsea, compute_annotation_gsea_series, compute_annotation_hits_from_protein_map, filter_annotation_hits, prepare_ranked_rows )
from routers.submission.analysis.volcano import handle_pairwise
from lib.cache.cache import db_cache_runtime
from datetime import timedelta
import numpy as np
import pandas as pd

ANNOTATION_ANALYSIS_CACHE_TIME = timedelta(hours=1)

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


def _resolve_universe(db: DatabaseABC, user: UserModel, submission_tags: Optional[str], proteome_tag: Optional[str]) -> List[str]:
    """Resolves the background universe for the annotation analysis endpoints.

    Either a semicolon-separated list of submission tags (union of the proteins
    quantified in these submissions, access-checked per submission) or a single
    proteome tag (all proteins of the proteome) must be provided.
    """
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
    return universe


def _filter_annotations_by_search_string(df: pd.DataFrame, search_string: Optional[str]) -> pd.DataFrame:
    if search_string is not None and len(search_string) > 0 and not df.empty:
        needle = search_string.lower()
        mask = df["annotation_tag"].str.lower().str.contains(needle) | df["text"].fillna("").str.lower().str.contains(needle)
        return df[mask]
    return df


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

    universe = _resolve_universe(db=db, user=user, submission_tags=submission_tags, proteome_tag=proteome_tag)

    universe_set = set(universe)
    target_in_universe = [t for t in dict.fromkeys(target) if t in universe_set]
    if len(target_in_universe) == 0:
        raise HTTPException(status_code=400, detail="No target proteins are part of the background universe.")

    overlap_counts = db.annotations.get_annotation_overlap_counts(
        universe_proteins=universe,
        target_proteins=target_in_universe,
        group_tag=group_tag,
        min_target_count=min_overlap,
    )

    overlap_counts = _filter_annotations_by_search_string(overlap_counts, search_string)

    cache_key = db_cache_runtime.make_cache_key(
        key_data={
            "kind": "enrichment",
            "user_tag": user.tag,
            "submission_tags": submission_tags,
            "proteome_tag": proteome_tag,
            "group_tag": group_tag,
            "search_string": search_string,
            "min_overlap": min_overlap,
            "limit": limit,
            "universe_size": len(universe),
            "target_size": len(target_in_universe),
        },
        namespace="annotation_analysis",
    )
    return db_cache_runtime.get_or_compute(
        cache_key=cache_key,
        compute_fn=lambda: enrichment_records(
            compute_annotation_enrichment(
                overlap_counts=overlap_counts,
                target_size=len(target_in_universe),
                universe_size=len(universe),
                min_overlap=min_overlap,
            ),
            limit=limit,
        ),
        cache_time=ANNOTATION_ANALYSIS_CACHE_TIME,
    )


@router.post("/analysis/shift", response_model=List[Dict])
def annotation_shift_analysis(
    request: AnnotationShiftRequestModel,
    user: UserModel = Depends(get_user_from_token),
    db: DatabaseABC = Depends(get_db),
) -> List[Dict]:
    """1D shift analysis ("systematic shifted annotations") of a per-protein value.

    For every annotation (optionally restricted to a group / search string) a
    two-sided Mann-Whitney U test compares the 1D values (e.g. log2FC of a
    volcano plot) of the annotation's member proteins against the values of
    all other proteins in the background universe. P-values are corrected with
    Benjamini-Hochberg FDR. ``direction`` ("up"/"down") is the sign of the mean
    difference of member vs. non-member values.
    """
    universe = _resolve_universe(
        db=db,
        user=user,
        submission_tags=";".join(request.submission_tags) if request.submission_tags else None,
        proteome_tag=request.proteome_tag,
    )
    universe_set = set(universe)

    protein_values = {
        tag: float(value)
        for tag, value in request.protein_values.items()
        if tag in universe_set and np.isfinite(value)
    }
    if len(protein_values) == 0:
        raise HTTPException(status_code=400, detail="No protein values are part of the background universe.")

    member_values = db.annotations.get_annotation_member_values(
        universe_proteins=sorted(universe_set),
        protein_values=protein_values,
        min_size=request.min_size,
        group_tag=request.group_tag,
    )
    member_values = _filter_annotations_by_search_string(member_values, request.search_string)

    cache_key = db_cache_runtime.make_cache_key(
        key_data={
            "kind": "shift",
            "user_tag": user.tag,
            "submission_tags": request.submission_tags,
            "proteome_tag": request.proteome_tag,
            "group_tag": request.group_tag,
            "search_string": request.search_string,
            "min_size": request.min_size,
            "limit": request.limit,
            "universe_size": len(universe),
            "n_values": len(protein_values),
        },
        namespace="annotation_analysis",
    )
    return db_cache_runtime.get_or_compute(
        cache_key=cache_key,
        compute_fn=lambda: enrichment_records(
            compute_annotation_shift_from_member_values(
                protein_values=protein_values,
                member_values=member_values,
                min_size=request.min_size,
            ),
            limit=request.limit,
        ),
        cache_time=ANNOTATION_ANALYSIS_CACHE_TIME,
    )

def _resolve_gsea_annotation_hits(
    db: DatabaseABC,
    user: UserModel,
    submission_tag: str,
    ca_tag_left: str,
    ca_tag_right: str,
    within_attribute_tags: Optional[str],
    within_ca_tags: Optional[str],
    annotation_tag: Optional[str],
    equal_variance: bool,
    group_tag: str,
    min_size: int,
    max_size: Optional[int],
):
    """Builds the ranked list + annotation hits for the GSEA analysis endpoints.

    The ranked list is computed server side from the same pairwise condition
    application comparison the volcano plot uses, so the client only sends the
    ca tags. Returns (ranked_rows, annotation_hits, suffix).
    """
    check_submission_access(submission_tag=submission_tag, user=user, db=db)
    if not db.annotation_groups.exists(group_tag):
        raise HTTPException(status_code=404, detail="Annotation group not found")

    sample_tags_left, sample_tags_right, sample_tags, suffix, _, _, _ = db.samples.handle_comparison(
        submission_tag=submission_tag,
        ca_tag_left=ca_tag_left,
        ca_tag_right=ca_tag_right,
        within_attribute_tags=within_attribute_tags,
        within_ca_tags=within_ca_tags,
        annotation_tag=annotation_tag,
    )

    stats = handle_pairwise(
        submission_tag=submission_tag,
        annotation_tag=annotation_tag,
        sample_tags=sample_tags,
        sample_tags_left=sample_tags_left,
        sample_tags_right=sample_tags_right,
        suffix=suffix,
        equal_variance=equal_variance,
        fdr=0.05,
        db=db,
    )

    ranked_rows = prepare_ranked_rows(stats, f"log2FC {suffix}")
    if ranked_rows.empty:
        raise HTTPException(status_code=404, detail="No proteins with a log2FC value for the given comparison.")

    universe_proteins = sorted({protein for proteins in ranked_rows["protein_tags"] for protein in proteins})

    protein_map = db.annotations.get_annotation_protein_map(
        universe_proteins=universe_proteins,
        group_tag=group_tag,
    )

    annotation_hits = compute_annotation_hits_from_protein_map(ranked_rows, protein_map)
    annotation_hits = filter_annotation_hits(annotation_hits, min_size=min_size, max_size=max_size)
    return ranked_rows, annotation_hits, suffix


@router.get("/analysis/gsea", response_model=List[Dict])
def annotation_gsea_analysis(
    submission_tag: str = Query(..., description="Submission tag of the pairwise comparison."),
    ca_tag_left: str = Query(..., description="Condition application tag of the left (up-regulated) group."),
    ca_tag_right: str = Query(..., description="Condition application tag of the right group."),
    within_attribute_tags: Optional[str] = Query(None, description="Optional semicolon-separated within attribute tags (as in the volcano plot)."),
    within_ca_tags: Optional[str] = Query(None, description="Optional semicolon-separated within condition application tags (as in the volcano plot)."),
    annotation_tag: Optional[str] = Query(None, description="Optional proteome annotation tag context (as in the volcano plot)."),
    equal_variance: bool = Query(True, description="Use equal variance for the pairwise t-test."),
    group_tag: str = Query(..., description="Annotation group whose annotations are tested."),
    min_size: int = Query(5, ge=1, description="Minimum number of ranked proteins per annotation to be tested."),
    max_size: Optional[int] = Query(None, ge=1, description="Maximum number of ranked proteins per annotation to be tested."),
    n_permutations: int = Query(1000, ge=10, le=10000, description="Monte Carlo permutations for the null distribution."),
    weight_p: float = Query(1.0, ge=0.0, le=2.0, description="GSEA weight exponent p (0 = unweighted, 1 = classic)."),
    limit: Optional[int] = Query(None, ge=1, description="Maximum number of results (after sorting by p-value)."),
    user: UserModel = Depends(get_user_from_token),
    db: DatabaseABC = Depends(get_db),
) -> List[Dict]:
    """Gene set enrichment style analysis of annotations for the ranked list.

    The ranked list is the log2FC of the pairwise condition application
    comparison (top of the list = most upregulated in `ca_tag_left` vs
    `ca_tag_right`). For every annotation of the given annotation group the
    classic weighted Kolmogorov-Smirnov running-sum enrichment score (GSEA) is
    computed, with Monte Carlo gene-set-permutation nominal p-values,
    same-sign NES normalization and Benjamini-Hochberg FDR correction.
    """
    cache_key = db_cache_runtime.make_cache_key(
        key_data={
            "kind": "gsea",
            "user_tag": user.tag,
            "submission_tag": submission_tag,
            "ca_tag_left": ca_tag_left,
            "ca_tag_right": ca_tag_right,
            "within_attribute_tags": within_attribute_tags,
            "within_ca_tags": within_ca_tags,
            "annotation_tag": annotation_tag,
            "equal_variance": equal_variance,
            "group_tag": group_tag,
            "min_size": min_size,
            "max_size": max_size,
            "n_permutations": n_permutations,
            "weight_p": weight_p,
            "limit": limit,
        },
        namespace="annotation_analysis",
    )
    return db_cache_runtime.get_or_compute(
        cache_key=cache_key,
        compute_fn=lambda: _annotation_gsea_records(
            db=db,
            user=user,
            submission_tag=submission_tag,
            ca_tag_left=ca_tag_left,
            ca_tag_right=ca_tag_right,
            within_attribute_tags=within_attribute_tags,
            within_ca_tags=within_ca_tags,
            annotation_tag=annotation_tag,
            equal_variance=equal_variance,
            group_tag=group_tag,
            min_size=min_size,
            max_size=max_size,
            n_permutations=n_permutations,
            weight_p=weight_p,
            limit=limit,
        ),
        cache_time=ANNOTATION_ANALYSIS_CACHE_TIME,
    )


def _annotation_gsea_records(
    db: DatabaseABC,
    user: UserModel,
    submission_tag: str,
    ca_tag_left: str,
    ca_tag_right: str,
    within_attribute_tags: Optional[str],
    within_ca_tags: Optional[str],
    annotation_tag: Optional[str],
    equal_variance: bool,
    group_tag: str,
    min_size: int,
    max_size: Optional[int],
    n_permutations: int,
    weight_p: float,
    limit: Optional[int],
) -> List[Dict]:
    ranked_rows, annotation_hits, suffix = _resolve_gsea_annotation_hits(
        db=db,
        user=user,
        submission_tag=submission_tag,
        ca_tag_left=ca_tag_left,
        ca_tag_right=ca_tag_right,
        within_attribute_tags=within_attribute_tags,
        within_ca_tags=within_ca_tags,
        annotation_tag=annotation_tag,
        equal_variance=equal_variance,
        group_tag=group_tag,
        min_size=min_size,
        max_size=max_size,
    )
    if not annotation_hits:
        return []

    table = compute_annotation_gsea(
        annotation_hits=annotation_hits,
        ranked_rows=ranked_rows,
        n_permutations=n_permutations,
        weight_p=weight_p,
    )
    records = table.to_dict(orient="records")
    if limit is not None:
        records = records[:limit]
    return records


@router.get("/analysis/gsea/series", response_model=Optional[Dict])
def annotation_gsea_series(
    submission_tag: str = Query(..., description="Submission tag of the pairwise comparison."),
    ca_tag_left: str = Query(..., description="Condition application tag of the left (up-regulated) group."),
    ca_tag_right: str = Query(..., description="Condition application tag of the right group."),
    within_attribute_tags: Optional[str] = Query(None),
    within_ca_tags: Optional[str] = Query(None),
    annotation_tag: Optional[str] = Query(None),
    equal_variance: bool = Query(True),
    group_tag: str = Query(..., description="Annotation group of the tested annotation."),
    plot_annotation_tag: str = Query(..., description="Tag of the annotation to plot."),
    min_size: int = Query(1, ge=1),
    max_size: Optional[int] = Query(None, ge=1),
    n_permutations: int = Query(1000, ge=10, le=10000),
    weight_p: float = Query(1.0, ge=0.0, le=2.0),
    user: UserModel = Depends(get_user_from_token),
    db: DatabaseABC = Depends(get_db),
) -> Optional[Dict]:
    """Running-sum series of one annotation for the GSEA plot.

    Same comparison and parameters as /analysis/gsea, but returns the full
    running-sum series, hit ranks and leading edge of the single annotation
    given by ``plot_annotation_tag``.
    """
    ranked_rows, annotation_hits, suffix = _resolve_gsea_annotation_hits(
        db=db,
        user=user,
        submission_tag=submission_tag,
        ca_tag_left=ca_tag_left,
        ca_tag_right=ca_tag_right,
        within_attribute_tags=within_attribute_tags,
        within_ca_tags=within_ca_tags,
        annotation_tag=annotation_tag,
        equal_variance=equal_variance,
        group_tag=group_tag,
        min_size=min_size,
        max_size=max_size,
    )
    if not annotation_hits:
        return None
    return compute_annotation_gsea_series(
        annotation_hits=annotation_hits,
        ranked_rows=ranked_rows,
        annotation_tag=plot_annotation_tag,
        n_permutations=n_permutations,
        weight_p=weight_p,
    )

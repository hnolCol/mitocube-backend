from typing import List, Optional, Dict

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from lib.database.Database import Database
from config.models.parameter import APIParamString
from config.models.annotations.annotations import AnnotationsModel
from scipy.stats import fisher_exact
import numpy as np

DB = Database.DB()


# ============================================================
# Input Schemas
# ============================================================

class FindAnnotationsInput(BaseModel):
    search_string: Optional[str] = Field(None, description="Free text search")
    group_tags: Optional[List[str]] = Field(None, description="Annotation group tags")
    protein_tags: Optional[List[str]] = Field(None, description="Protein tags")
    submission_tags: Optional[List[str]] = Field(None, description="Submission tags")
    limit: Optional[int] = Field(None, description="Max number of results")
    group_by_group: bool = Field(False, description="Return grouped results")


class TagInput(BaseModel):
    tag: str = Field(..., description="Annotation tag")


class ProteinAnnotateCheckInput(BaseModel):
    tag: str = Field(..., description="Annotation tag")
    protein_tag: str = Field(..., description="Protein tag or semicolon-separated list")


class ProteinAnnotateMultiInput(BaseModel):
    tag: str = Field(..., description="Annotation tag")
    protein_tags: str = Field(..., description="Semicolon-separated protein tags")


class AnnotationGroupFindInput(BaseModel):
    search_string: Optional[str] = Field(None, description="Search text")
    protein_tag: Optional[str] = Field(None, description="Protein tag filter")


class AnnotationGroupInput(BaseModel):
    group_tag: str = Field(..., description="Annotation group tag")


class AnnotationGroupLimitInput(BaseModel):
    group_tag: str = Field(..., description="Annotation group tag")
    limit: int = Field(20, description="Max results")


class ProteinCountInput(BaseModel):
    tag: str = Field(..., description="Annotation tag")


class ProteinListInput(BaseModel):
    tag: str = Field(..., description="Annotation tag")
    submission_tag: Optional[str] = Field(None, description="Optional submission filter")


class FisherAnalysisInput(BaseModel):
    submission_tag: str
    target_proteins: List[str]
    group_tag: str

class AnnotationOutput(AnnotationsModel):
    pass 
# ============================================================
# Annotation Tools (READ ONLY)
# ============================================================

@tool("find_annotations", args_schema=FindAnnotationsInput)
def find_annotations(
    search_string: Optional[str] = None,
    group_tags: Optional[List[str]] = None,
    protein_tags: Optional[List[str]] = None,
    submission_tags: Optional[List[str]] = None,
    limit: Optional[int] = None,
    group_by_group: bool = False,
) -> List[str]:
    """
    Find annotations based on search filters.
    """
    return DB.annotations.find(
        search_string=search_string,
        group_tags=group_tags,
        protein_tags=protein_tags,
        submission_tags=submission_tags,
        limit=limit,
        group_by_group=group_by_group,
    )



@tool("get_annotation", args_schema=TagInput)
def get_annotation(tag: str) -> AnnotationOutput:
    """
    Get a single annotation by tag.
    """
    if not DB.annotations.exists(tag):
        return None
    return DB.annotations.get(tag=tag)


@tool("annotation_exists", args_schema=TagInput)
def annotation_exists(tag: str) -> bool:
    """
    Check if an annotation exists.
    """
    return DB.annotations.exists(tag)


@tool("get_annotation_count", args_schema=ProteinCountInput)
def get_annotation_count() -> int:
    """
    Count the number of annotations present in the database. 
    """
    return DB.annotations.count()

@tool("is_protein_annotated_with", args_schema=ProteinAnnotateCheckInput)
def is_protein_annotated_with(tag: str, protein_tag: str) -> bool:
    """
    Check if a protein (or set of proteins) is annotated with a given annotation.
    """
    if not DB.annotations.exists(tag):
        return False

    if ";" in protein_tag:
        protein_tags = APIParamString(param=protein_tag).param
    else:
        protein_tags = [protein_tag]

    bool_idx = DB.annotations.isin(tag=tag, protein_tags=protein_tags)

    return bool(np.any(bool_idx.values)) if len(bool_idx) > 0 else False


@tool("are_proteins_annotated_with", args_schema=ProteinAnnotateMultiInput)
def are_proteins_annotated_with(tag: str, protein_tags: List[str]) -> List[Dict]:
    """
    Check annotation membership for multiple proteins.
    """
    if not DB.annotations.exists(tag):
        return []

    bool_idx = DB.annotations.isin(tag=tag, protein_tags=protein_tags)

    return [
        {
            "protein_tag": protein_tag,
            "isin": bool_idx[protein_tag],
            "annotation_tag": tag,
        }
        for protein_tag in bool_idx.index
    ]


@tool("get_annotation_protein_count", args_schema=ProteinCountInput)
def get_annotation_protein_count(tag: str) -> int:
    """
    Count proteins linked to an annotation.
    """
    if not DB.annotations.exists(tag):
        return 0
    return DB.annotations.count_proteins(tag)


@tool("find_annotation_groups", args_schema=AnnotationGroupFindInput)
def find_annotation_groups(
    search_string: Optional[str] = None,
    protein_tag: Optional[str] = None,
    return_annotations: bool = False,
    limit : int = None
) -> List[str]:
    """
    Find annotation groups.
    return_annotations : bool
        If True, return annotations linked to the groups. Will be returned. This is useful to get annotation groups along with their annotations. (e.g. searching for all)

    limit : int
        Limit the number of results.

    Returns
        List[str] | List[Dict]
        Annotation group tags. If return_annotations is True, a list of dicts with keys 'tag' and 'annotation_tags' is returned.
    """
    return DB.annotation_groups.find(
        search_string=search_string,
        protein_tag=protein_tag,
        return_annotations=return_annotations,
        limit=limit
    )


@tool("get_annotation_group", args_schema=AnnotationGroupInput)
def get_annotation_group(group_tag: str):
    """
    Get annotation group tag.
    """
    if not DB.annotation_groups.exists(group_tag):
        return None

    return DB.annotation_groups.get(tag=group_tag)


@tool("get_annotations_in_group", args_schema=AnnotationGroupLimitInput)
def get_annotations_in_group(group_tag: str, limit: int = 20) -> List[str]:
    """
    Get annotation tags in a group.
    """
    if not DB.annotation_groups.exists(group_tag):
        return []

    return DB.annotation_groups.get_annotations(group_tag, limit=limit)


@tool("count_annotations_in_group", args_schema=AnnotationGroupInput)
def count_annotations_in_group(group_tag: str) -> int:
    """
    Count annotations in a group.
    """
    if not DB.annotation_groups.exists(group_tag):
        return 0

    return DB.annotation_groups.count_annotations(group_tag)


@tool("get_proteins_for_annotation", args_schema=ProteinListInput)
def get_proteins_for_annotation(tag: str, submission_tag: Optional[str] = None) -> List[str]:
    """
    Get proteins associated with an annotation.
    """
    if not DB.annotations.exists(tag):
        return []

    return DB.annotations.get_protein_tags(tag, submission_tag)


# ============================================================
# Fisher Analysis (READ ONLY)
# ============================================================

@tool("fisher_annotation_analysis", args_schema=FisherAnalysisInput)
def fisher_annotation_analysis(
    submission_tag: str,
    target_proteins: List[str],
    group_tag: str,
) -> List[Dict]:
    """
    Perform Fisher exact test for annotation enrichment.
    """

    all_proteins = set(DB.submissions.get_proteins_in_submission(submission_tag))

    if not all_proteins:
        return []

    target = set(target_proteins) & all_proteins
    general = all_proteins - target

    if not target:
        return []

    annotation_to_proteins = DB.annotations.get_proteins_by_annotation_group(
        group_tag=group_tag,
        submission_tag=submission_tag,
    )

    results = []

    for annotation_tag, annotated_proteins in annotation_to_proteins.items():
        annotated_set = set(annotated_proteins)

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


ANNOTATION_TOOLS = [
    find_annotation_groups,
    get_annotation_group,
    get_annotations_in_group,
    count_annotations_in_group,
    get_proteins_for_annotation,
    fisher_annotation_analysis,
    get_annotation_count
]
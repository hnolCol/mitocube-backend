from typing import Dict, List, Literal, Tuple

from fastapi import APIRouter, Depends, HTTPException

from lib.database.Database import get_db
from lib.database.abstract.Database import DatabaseABC
from config.models.user import UserModel
from config.models.plots.projection import ProteomeProjectionResponseModel, ProteomeProjectionDriverResponseModel, ProteomeProjectionEffectResponseModel, ProjectionDriverModel
from config.exceptions.HTTPExceptions import no_data_found_http_exception
from services.users import get_user_from_token
from services.statistics.projection import (
    assemble_pooled_pca,
    compute_condition_effects,
    enrich_result_with_conditions,
    find_driver,
    get_sample_condition_map,
    get_submission_block_cached,
    protein_condition_association,
    resolve_visible_submission_tags,
    result_cache_key,
    PROJECTION_RESULT_CACHE_TIME,
    DEFAULT_MIN_VALID_FRACTION,
)
from lib.cache.cache import db_cache_runtime

router = APIRouter(dependencies=[Depends(get_user_from_token)],
    prefix="/api/stats/proteomes",
    tags=["Proteomes", "Statistics"],
    )


def _resolve_visible_blocks(db: DatabaseABC, user: UserModel, proteome_tag: str,
                            min_valid_fraction: float) -> Tuple[List[str], List[Dict]]:
    """Resolves the submissions of the proteome that are inside the requesting user's
    submission scope and returns their (cached) projection blocks."""
    proteome_submission_tags = db.submissions.get_tags_by_proteome(proteome_tag)
    scope = db.submission_filter.get_user_submission_scope_tags(user_tag=user.tag)
    visible_tags = resolve_visible_submission_tags(scope, proteome_submission_tags)

    blocks = [block for tag in visible_tags
              if (block := get_submission_block_cached(db, tag, min_valid_fraction)) is not None]
    if not blocks:
        raise no_data_found_http_exception
    return visible_tags, blocks


def _compute_pooled_projection(db: DatabaseABC, user: UserModel, proteome_tag: str,
                               method: str, n_components: int, min_valid_fraction: float) -> Tuple[Dict, List[Dict]]:
    """Computes (or fetches from cache) the pooled projection over all submissions of the
    proteome that are inside the requesting user's submission scope. The result cache key
    embeds a hash of the visible submission tags, so results are never shared across scopes.
    Returns the result dict and the submission blocks it was built from."""
    visible_tags, blocks = _resolve_visible_blocks(db, user, proteome_tag, min_valid_fraction)

    def compute():
        try:
            result = assemble_pooled_pca(blocks, n_components=n_components)
        except ValueError as e:
            raise no_data_found_http_exception from e
        return {
            "proteome_tag": proteome_tag,
            "method": method,
            "n_components": result["n_components"],
            "variance_explained": result["variance_explained"],
            "n_proteins": result["n_proteins"],
            "n_submissions": len(blocks),
            "submission_tags": sorted(block["submission_tag"] for block in blocks),
            "points": result["points"],
            "drivers": result["drivers"],
        }

    result = db_cache_runtime.get_or_compute(
        cache_key=result_cache_key(proteome_tag, visible_tags, method=method,
                                   n_components=n_components, min_valid_fraction=min_valid_fraction),
        compute_fn=compute,
        cache_time=PROJECTION_RESULT_CACHE_TIME,
    )
    return result, blocks


@router.get("/{proteome_tag}/projection", tags=["Dimensional reduction", "PCA"])
def get_proteome_projection(
    proteome_tag: str,
    method: Literal["pca"] = "pca",
    n_components: int = 2,
    min_valid_fraction: float = DEFAULT_MIN_VALID_FRACTION,
    user: UserModel = Depends(get_user_from_token),
    db: DatabaseABC = Depends(get_db),
) -> ProteomeProjectionResponseModel:
    """
    Returns a pooled PCA projection of all samples of the submissions associated with the
    given proteome that the requesting user has access to. Per-submission z-scored
    quantification matrices are cached per submission; the user's submission scope is
    applied when assembling the pooled matrix and the PCA is computed fresh per scope.
    """
    if not db.proteomes.exists(tag=proteome_tag):
        raise HTTPException(status_code=404, detail="Proteome not found")
    result, _ = _compute_pooled_projection(
        db, user, proteome_tag, method=method, n_components=n_components,
        min_valid_fraction=min_valid_fraction)
    sample_ca_map = get_sample_condition_map(db, result["submission_tags"])
    return ProteomeProjectionResponseModel(**enrich_result_with_conditions(result, sample_ca_map))


@router.get("/{proteome_tag}/projection/drivers/{protein_tag}", tags=["Dimensional reduction", "PCA"])
def get_proteome_projection_driver(
    proteome_tag: str,
    protein_tag: str,
    n_components: int = 4,
    min_valid_fraction: float = DEFAULT_MIN_VALID_FRACTION,
    user: UserModel = Depends(get_user_from_token),
    db: DatabaseABC = Depends(get_db),
) -> ProteomeProjectionDriverResponseModel:
    """
    Returns the driver loadings of a single protein group within the pooled PCA projection
    of the proteome (the same user-scoped projection as /projection, computed with up to
    n_components components). Useful for a protein-specific view. Returns 404 if the
    protein group does not exist or is not part of the pooled projection universe.
    """
    if not db.proteomes.exists(tag=proteome_tag):
        raise HTTPException(status_code=404, detail="Proteome not found")
    if not db.protein_groups.exists(tag=protein_tag):
        raise HTTPException(status_code=404, detail="Protein group not found")

    result, blocks = _compute_pooled_projection(db, user, proteome_tag, method="pca",
                                                 n_components=n_components,
                                                 min_valid_fraction=min_valid_fraction)
    driver = find_driver(result, protein_tag)
    if driver is None:
        raise HTTPException(status_code=404, detail="Protein group is not quantified in enough submissions of this proteome to be part of the projection universe.")
    sample_ca_map = get_sample_condition_map(db, result["submission_tags"])
    return ProteomeProjectionDriverResponseModel(
        proteome_tag=proteome_tag,
        protein_tag=protein_tag,
        n_components=result["n_components"],
        variance_explained=result["variance_explained"],
        n_submissions=result["n_submissions"],
        submission_tags=result["submission_tags"],
        driver=ProjectionDriverModel(**driver),
        condition_associations=protein_condition_association(blocks, sample_ca_map, protein_tag),
    )


@router.get("/{proteome_tag}/projection/effects/{ca_tag}", tags=["Dimensional reduction", "PCA"])
def get_proteome_projection_condition_effects(
    proteome_tag: str,
    ca_tag: str,
    limit: int = 50,
    min_valid_fraction: float = DEFAULT_MIN_VALID_FRACTION,
    user: UserModel = Depends(get_user_from_token),
    db: DatabaseABC = Depends(get_db),
) -> ProteomeProjectionEffectResponseModel:
    """
    Quantitatively assigns the effect of a condition application across the proteome: for
    every protein group quantified in the user's visible submissions of this proteome, the
    effect is the mean z-score in samples carrying the condition application minus the mean
    z-score in all other samples, ranked by absolute effect (most affected proteins first),
    with a standardized effect size (Cohen's d). Computed on the same user-scoped pooled
    data as the projection endpoints.
    """
    if not db.proteomes.exists(tag=proteome_tag):
        raise HTTPException(status_code=404, detail="Proteome not found")
    _, blocks = _resolve_visible_blocks(db, user, proteome_tag, min_valid_fraction)
    submission_tags = sorted(block["submission_tag"] for block in blocks)
    sample_ca_map = get_sample_condition_map(db, submission_tags)
    if not any(ca_tag in cas for cas in sample_ca_map.values()):
        raise HTTPException(status_code=404, detail="Condition application not found among the samples of the accessible submissions of this proteome.")
    effects = compute_condition_effects(blocks, sample_ca_map, ca_tag, limit=limit)
    return ProteomeProjectionEffectResponseModel(
        proteome_tag=proteome_tag,
        ca_tag=ca_tag,
        n_submissions=len(blocks),
        submission_tags=submission_tags,
        n_proteins=effects["n_proteins"],
        effects=effects["effects"],
    )

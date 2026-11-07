from typing import Literal

from fastapi import APIRouter, Depends, HTTPException

from lib.database.Database import get_db
from lib.database.abstract.Database import DatabaseABC
from config.models.user import UserModel
from config.models.plots.projection import ProteomeProjectionResponseModel
from config.exceptions.HTTPExceptions import no_data_found_http_exception
from services.users import get_user_from_token
from services.statistics.projection import (
    assemble_pooled_pca,
    get_submission_block_cached,
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

    proteome_submission_tags = db.submissions.get_tags_by_proteome(proteome_tag)
    scope = db.submission_filter.get_user_submission_scope_tags(user_tag=user.tag)
    visible_tags = resolve_visible_submission_tags(scope, proteome_submission_tags)

    blocks = [block for tag in visible_tags
              if (block := get_submission_block_cached(db, tag, min_valid_fraction)) is not None]
    if not blocks:
        raise no_data_found_http_exception

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

    return ProteomeProjectionResponseModel(**db_cache_runtime.get_or_compute(
        cache_key=result_cache_key(proteome_tag, visible_tags, method=method,
                                   n_components=n_components, min_valid_fraction=min_valid_fraction),
        compute_fn=compute,
        cache_time=PROJECTION_RESULT_CACHE_TIME,
    ))

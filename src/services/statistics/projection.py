import hashlib
import json
import math
from collections import Counter
from datetime import timedelta
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA

from lib.cache.cache import db_cache_runtime

PROJECTION_BLOCK_NAMESPACE = "projection_block"
PROJECTION_RESULT_NAMESPACE = "proteome_projection"
PROJECTION_BLOCK_CACHE_TIME = timedelta(hours=1)
PROJECTION_RESULT_CACHE_TIME = timedelta(minutes=10)

DEFAULT_MIN_VALID_FRACTION = 0.5
DEFAULT_MIN_BLOCK_OCCURRENCE = 2
DEFAULT_MIN_BLOCK_FRACTION = 0.05


def block_cache_key(submission_tag: str, min_valid_fraction: float = DEFAULT_MIN_VALID_FRACTION) -> str:
    return db_cache_runtime.make_cache_key(
        key_data={"submission_tag": submission_tag, "min_valid_fraction": min_valid_fraction},
        namespace=PROJECTION_BLOCK_NAMESPACE,
    )


def result_cache_key(proteome_tag: str, visible_submission_tags: List[str], method: str = "pca",
                     n_components: int = 2, min_valid_fraction: float = DEFAULT_MIN_VALID_FRACTION) -> str:
    """Cache key for a pooled projection result. The key includes a hash of the user's
    visible submission tags, so results are never shared across different scopes."""
    scope_hash = hashlib.sha256(json.dumps(sorted(visible_submission_tags)).encode()).hexdigest()
    return db_cache_runtime.make_cache_key(
        key_data={
            "proteome_tag": proteome_tag,
            "method": method,
            "n_components": n_components,
            "min_valid_fraction": min_valid_fraction,
            "scope_hash": scope_hash,
        },
        namespace=f"{PROJECTION_RESULT_NAMESPACE}:{proteome_tag}",
    )


def resolve_visible_submission_tags(scope: Optional[List[str]], proteome_submission_tags: List[str]) -> List[str]:
    """Intersects the proteome's submissions with the user's submission scope.
    A scope of None means unrestricted (curator/admin) and returns all proteome submissions;
    an empty scope (guest) returns nothing."""
    if scope is None:
        return list(proteome_submission_tags)
    scope_set = set(scope)
    return [tag for tag in proteome_submission_tags if tag in scope_set]


def build_submission_block(db, submission_tag: str, min_valid_fraction: float = DEFAULT_MIN_VALID_FRACTION) -> Optional[Dict]:
    """Builds the cacheable per-submission block: the per-sample z-scored quantification
    matrix (samples x protein groups), restricted to protein groups quantified in at least
    min_valid_fraction of the submission's samples, with remaining missing values imputed
    as 0 (neutral for z-scored data)."""
    matrix = db.submissions.get_zscore_matrix(submission_tag)
    if matrix is None or matrix.empty:
        return None
    valid_fraction = matrix.notna().mean(axis=1)
    matrix = matrix.loc[valid_fraction >= min_valid_fraction]
    if matrix.empty or matrix.shape[1] == 0:
        return None
    sample_matrix = matrix.T.fillna(0.0).astype(np.float32)
    return {
        "submission_tag": submission_tag,
        "sample_tags": matrix.columns.tolist(),
        "proteins": matrix.index.tolist(),
        "matrix": sample_matrix,
    }


def get_submission_block_cached(db, submission_tag: str, min_valid_fraction: float = DEFAULT_MIN_VALID_FRACTION) -> Optional[Dict]:
    return db_cache_runtime.get_or_compute(
        cache_key=block_cache_key(submission_tag, min_valid_fraction),
        compute_fn=lambda: build_submission_block(db, submission_tag, min_valid_fraction),
        cache_time=PROJECTION_BLOCK_CACHE_TIME,
    )


def assemble_pooled_pca(blocks: List[Dict], n_components: int = 2,
                        min_block_occurrence: int = DEFAULT_MIN_BLOCK_OCCURRENCE,
                        min_block_fraction: float = DEFAULT_MIN_BLOCK_FRACTION) -> Dict:
    """Computes a pooled PCA over the samples of all given submission blocks. The protein
    universe is restricted to protein groups present in enough blocks; blocks are aligned
    on that universe (missing proteins contribute 0, consistent with the zero-imputation in
    build_submission_block) and stacked, then PCA is fitted on the pooled matrix."""
    if not blocks:
        raise ValueError("No submission blocks to project.")
    counts = Counter(protein for block in blocks for protein in block["proteins"])
    threshold = max(min_block_occurrence, math.ceil(min_block_fraction * len(blocks)))
    universe = sorted(protein for protein, count in counts.items() if count >= threshold)
    if not universe:
        raise ValueError("No protein groups shared across enough submissions to project.")

    frames = []
    owners = []
    for block in blocks:
        aligned = block["matrix"].reindex(columns=universe).fillna(0.0)
        frames.append(aligned)
        owners.extend((block["submission_tag"], sample_tag) for sample_tag in aligned.index)

    X = pd.concat(frames, axis=0, ignore_index=True).to_numpy(dtype=np.float64)
    n_comp = max(1, min(n_components, X.shape[1], max(1, X.shape[0] - 1)))
    pca = PCA(n_components=n_comp)
    scores = pca.fit_transform(X)

    points = [
        {
            "sample_tag": sample_tag,
            "submission_tag": submission_tag,
            "components": [float(v) for v in row],
        }
        for (submission_tag, sample_tag), row in zip(owners, scores)
    ]
    loadings = pca.components_.T  # proteins x components
    drivers = [
        {
            "tag": protein,
            "components": [float(v) for v in row],
        }
        for protein, row in zip(universe, loadings)
    ]
    return {
        "n_components": n_comp,
        "variance_explained": [float(v) for v in pca.explained_variance_ratio_],
        "n_proteins": len(universe),
        "points": points,
        "drivers": drivers,
    }


def find_driver(result: Dict, protein_tag: str) -> Optional[Dict]:
    """Returns the driver entry (loadings on all components) of a single protein group
    from a pooled projection result, or None if the protein is not in the pooled universe."""
    for driver in result["drivers"]:
        if driver["tag"] == protein_tag:
            return driver
    return None


def invalidate_projection_caches(db, submission_tag: str) -> None:
    """Invalidates the cached projection block of a submission and all pooled projection
    results of the proteomes the submission belongs to. Called after quantification or
    statistics writes."""
    db_cache_runtime.invalidate(block_cache_key(submission_tag))
    for proteome_tag in db.submissions.get_proteomes(submission_tag):
        db_cache_runtime.invalidate_namespace(f"{PROJECTION_RESULT_NAMESPACE}:{proteome_tag}")

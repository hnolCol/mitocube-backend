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


def compute_universe(blocks: List[Dict], min_block_occurrence: int = DEFAULT_MIN_BLOCK_OCCURRENCE,
                     min_block_fraction: float = DEFAULT_MIN_BLOCK_FRACTION) -> List[str]:
    """The pooled protein universe: protein groups present in at least max(min_block_occurrence,
    min_block_fraction * n_blocks) of the given blocks."""
    counts = Counter(protein for block in blocks for protein in block["proteins"])
    threshold = max(min_block_occurrence, math.ceil(min_block_fraction * len(blocks)))
    return sorted(protein for protein, count in counts.items() if count >= threshold)


def assemble_pooled_pca(blocks: List[Dict], n_components: int = 2,
                        min_block_occurrence: int = DEFAULT_MIN_BLOCK_OCCURRENCE,
                        min_block_fraction: float = DEFAULT_MIN_BLOCK_FRACTION) -> Dict:
    """Computes a pooled PCA over the samples of all given submission blocks. The protein
    universe is restricted to protein groups present in enough blocks; blocks are aligned
    on that universe (missing proteins contribute 0, consistent with the zero-imputation in
    build_submission_block) and stacked, then PCA is fitted on the pooled matrix."""
    if not blocks:
        raise ValueError("No submission blocks to project.")
    universe = compute_universe(blocks, min_block_occurrence, min_block_fraction)
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


def get_sample_condition_map(db, submission_tags: List[str]) -> Dict[tuple, List[str]]:
    """Maps (submission_tag, sample_tag) to the sorted list of condition application tags
    of that sample, for the given submissions."""
    mapping: Dict[tuple, List[str]] = {}
    for submission_tag in submission_tags:
        ca = db.samples.get_condition_applications_by_sample_for_submission(
            submission_tag=submission_tag, sort_ca_tags=True, return_sample_index=False)
        for sample_tag, row in ca.iterrows():
            mapping[(submission_tag, sample_tag)] = sorted({str(v) for v in row.dropna().unique()})
    return mapping


def enrich_result_with_conditions(result: Dict, sample_ca_map: Dict[tuple, List[str]]) -> Dict:
    """Annotates each point of a pooled projection result with the condition applications of
    its sample and adds condition centroids: for each condition application tag, the mean
    component scores over all samples that have it. Shows which conditions align with which
    principal components. Returns a new dict; the cached result is not mutated."""
    enriched = dict(result)
    points = []
    sums: Dict[str, List[float]] = {}
    counts: Dict[str, int] = {}
    n_comp = result["n_components"]
    for point in result["points"]:
        cas = sample_ca_map.get((point["submission_tag"], point["sample_tag"]), [])
        points.append({**point, "condition_applications": cas})
        for ca in cas:
            acc = sums.setdefault(ca, [0.0] * n_comp)
            for i, v in enumerate(point["components"]):
                acc[i] += v
            counts[ca] = counts.get(ca, 0) + 1
    centroids = [
        {
            "condition_application_tag": ca,
            "count": counts[ca],
            "components": [s / counts[ca] for s in sums[ca]],
        }
        for ca in sorted(sums)
    ]
    enriched["points"] = points
    enriched["condition_centroids"] = centroids
    return enriched


def protein_condition_association(blocks: List[Dict], sample_ca_map: Dict[tuple, List[str]], protein_tag: str) -> List[Dict]:
    """For a single protein group, computes the mean z-scored quantification per condition
    application over all samples (of the given blocks) that carry the condition, sorted by
    mean descending. Connects the protein's driver loadings to the conditions where it is
    most highly expressed."""
    sums: Dict[str, float] = {}
    counts: Dict[str, int] = {}
    for block in blocks:
        matrix = block["matrix"]
        if protein_tag not in matrix.columns:
            continue
        for sample_tag in matrix.index:
            value = float(matrix.at[sample_tag, protein_tag])
            for ca in sample_ca_map.get((block["submission_tag"], sample_tag), []):
                sums[ca] = sums.get(ca, 0.0) + value
                counts[ca] = counts.get(ca, 0) + 1
    return [
        {
            "condition_application_tag": ca,
            "mean_z": sums[ca] / counts[ca],
            "n_samples": counts[ca],
        }
        for ca in sorted(sums, key=lambda c: sums[c] / counts[c], reverse=True)
    ]


def compute_condition_effects(blocks: List[Dict], sample_ca_map: Dict[tuple, List[str]],
                              ca_tag: str, limit: int = 50) -> Dict:
    """Quantitative effect of a condition application per protein group, computed on the
    pooled z-scored blocks: effect = mean z in samples carrying the CA minus mean z in all
    other samples, plus a Cohen's-d style standardized effect using the pooled within-group
    standard deviation. Only proteins quantified in both groups are ranked. Returns the top
    `limit` proteins by absolute effect, most affected first."""
    in_stats: Dict[str, List[float]] = {}
    out_stats: Dict[str, List[float]] = {}
    for block in blocks:
        matrix = block["matrix"]
        rows_in = [s for s in matrix.index
                   if ca_tag in sample_ca_map.get((block["submission_tag"], s), [])]
        rows_out = [s for s in matrix.index if s not in set(rows_in)]
        for rows, stats in ((rows_in, in_stats), (rows_out, out_stats)):
            if not rows:
                continue
            sub = matrix.loc[rows]
            sums = sub.sum()
            sumsqs = (sub.astype(np.float64) ** 2).sum()
            for protein in matrix.columns:
                acc = stats.setdefault(protein, [0.0, 0.0, 0])
                acc[0] += float(sums[protein])
                acc[1] += float(sumsqs[protein])
                acc[2] += len(rows)

    effects = []
    for protein in set(in_stats) & set(out_stats):
        si, sqi, ni = in_stats[protein]
        so, sqo, no = out_stats[protein]
        mean_in = si / ni
        mean_out = so / no
        var_in = max(sqi / ni - mean_in ** 2, 0.0)
        var_out = max(sqo / no - mean_out ** 2, 0.0)
        pooled_var = ((ni - 1) * var_in + (no - 1) * var_out) / max(ni + no - 2, 1)
        pooled_sd = math.sqrt(pooled_var)
        effect = mean_in - mean_out
        effects.append({
            "tag": protein,
            "effect": effect,
            "mean_z_in": mean_in,
            "mean_z_out": mean_out,
            "n_in": ni,
            "n_out": no,
            "cohens_d": effect / pooled_sd if pooled_sd > 0 else None,
        })
    effects.sort(key=lambda e: abs(e["effect"]), reverse=True)
    return {
        "ca_tag": ca_tag,
        "n_proteins": len(effects),
        "effects": effects[:limit],
    }


def get_ca_attribute_map(db, submission_tags: List[str]) -> Dict[str, str]:
    """Maps each condition application tag to the attribute tag it belongs to, based on the
    condition applications of the given submissions (e.g. ca_tag -> 'att_chemical_compound')."""
    mapping: Dict[str, str] = {}
    for submission_tag in submission_tags:
        ca = db.samples.get_condition_applications_by_sample_for_submission(
            submission_tag=submission_tag, sort_ca_tags=True, return_sample_index=False)
        for attribute_tag, column in ca.items():
            for value in column.dropna().unique():
                mapping[str(value)] = attribute_tag
    return mapping


def compute_ca_separation(result: Dict, sample_ca_map: Dict[tuple, List[str]], ca_tag: str) -> float:
    """Quantitative separation of a condition application on the projection: the squared
    distance between the mean component scores of samples with and without the CA, weighted
    by the explained variance of each component. Higher means the CA separates samples more
    along the projected axes."""
    n_comp = result["n_components"]
    variance_explained = result["variance_explained"]
    in_sum = [0.0] * n_comp
    out_sum = [0.0] * n_comp
    n_in = 0
    n_out = 0
    for point in result["points"]:
        cas = sample_ca_map.get((point["submission_tag"], point["sample_tag"]), [])
        has_ca = ca_tag in cas
        for i, value in enumerate(point["components"]):
            if has_ca:
                in_sum[i] += value
            else:
                out_sum[i] += value
        if has_ca:
            n_in += 1
        else:
            n_out += 1
    if n_in == 0 or n_out == 0:
        return 0.0
    separation = 0.0
    for c in range(n_comp):
        diff = in_sum[c] / n_in - out_sum[c] / n_out
        separation += variance_explained[c] * diff * diff
    return separation


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

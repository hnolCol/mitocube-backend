"""Gene set enrichment (GSEA) style analysis of annotations against a ranked list.

The ranked list is built server side from the same pairwise condition
application comparison the volcano plot uses (``ca_tag_left`` vs
``ca_tag_right`` of a submission), so the client only sends the condition
application tags and the annotation group to test. For every annotation of the
group the weighted Kolmogorov-Smirnov running-sum enrichment score (classic
GSEA) is computed on the log2FC-ranked protein list, with Monte Carlo
gene-set-permutation nominal p-values, NES normalization and Benjamini-Hochberg
FDR correction. Pure statistics helpers, separated from the database layer so
they can be unit-tested without a graph database.
"""
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy.stats import false_discovery_control

from services.gsea import running_sum_enrichment_score

GSEA_COLUMNS = [
    "annotation_tag",
    "text",
    "size",
    "es",
    "nes",
    "p_value",
    "fdr",
]


def prepare_ranked_rows(stats: pd.DataFrame, log2fc_field: str) -> pd.DataFrame:
    """Builds the ranked list from a pairwise comparison stats table.

    ``stats`` is the output of the volcano ``handle_pairwise`` helper: one row
    per protein group with the protein group ``tag`` (semicolon-separated
    protein tags) and the ``log2fc_field`` column (log2FC of the comparison).
    Rows without a value are dropped, the rest is sorted descending (most
    upregulated first). Returns a DataFrame with columns ``tag``,
    ``protein_tags`` (list) and ``log2fc``.
    """
    if stats is None or stats.empty or log2fc_field not in stats.columns:
        return pd.DataFrame(columns=["tag", "protein_tags", "log2fc"])
    work = stats[["tag", log2fc_field]].dropna(subset=[log2fc_field]).copy()
    if work.empty:
        return pd.DataFrame(columns=["tag", "protein_tags", "log2fc"])
    work["protein_tags"] = work["tag"].astype(str).str.split(";")
    work = work.rename(columns={log2fc_field: "log2fc"})
    work = work.sort_values("log2fc", ascending=False, kind="mergesort").reset_index(drop=True)
    return work[["tag", "protein_tags", "log2fc"]]


def compute_annotation_hits_from_protein_map(
    ranked_rows: pd.DataFrame,
    protein_map: pd.DataFrame,
) -> Dict[str, Tuple[np.ndarray, str]]:
    """Maps each annotation's member proteins onto indices in the ranked list.

    ``protein_map`` must have the columns ``annotation_tag``, ``text`` and
    ``protein_tags`` (as returned by the database layer). Returns a dict of
    ``annotation_tag -> (hit row indices in the ranked list, text)``. A ranked
    row (protein group) is a hit of an annotation if ANY of its proteins is
    annotated by it.
    """
    if ranked_rows.empty or protein_map is None or protein_map.empty:
        return {}

    protein_to_rows: Dict[str, List[int]] = {}
    for row_index, proteins in enumerate(ranked_rows["protein_tags"]):
        for protein_tag in proteins:
            protein_to_rows.setdefault(protein_tag, []).append(row_index)

    result: Dict[str, Tuple[np.ndarray, str]] = {}
    for _, row in protein_map.iterrows():
        hit_rows = set()
        for protein_tag in row["protein_tags"]:
            hit_rows.update(protein_to_rows.get(protein_tag, []))
        if not hit_rows:
            continue
        indices = np.fromiter(sorted(hit_rows), dtype=np.int64, count=len(hit_rows))
        result[row["annotation_tag"]] = (indices, row.get("text"))
    return result


def filter_annotation_hits(
    annotation_hits: Dict[str, Tuple[np.ndarray, str]],
    min_size: int = 5,
    max_size: Optional[int] = None,
) -> Dict[str, Tuple[np.ndarray, str]]:
    """Drops annotations outside the [min_size, max_size] size band."""
    filtered = {}
    for annotation_tag, (indices, text) in annotation_hits.items():
        if indices.size < min_size:
            continue
        if max_size is not None and indices.size > max_size:
            continue
        filtered[annotation_tag] = (indices, text)
    return filtered


def compute_annotation_gsea(
    annotation_hits: Dict[str, Tuple[np.ndarray, str]],
    ranked_rows: pd.DataFrame,
    n_permutations: int = 1000,
    weight_p: float = 1.0,
    seed: int = 0,
) -> pd.DataFrame:
    """Computes GSEA ES, NES, nominal p-values and BH FDR for all annotations.

    Returns a DataFrame with the columns of ``GSEA_COLUMNS``, one row per
    tested annotation, sorted by ascending p-value.
    """
    result = pd.DataFrame(columns=GSEA_COLUMNS)
    if ranked_rows.empty or not annotation_hits:
        return result

    from services.gsea import gsea_p_values

    scores = ranked_rows["log2fc"].to_numpy(dtype=np.float64)
    tags = [tag for tag in annotation_hits.keys()]
    hits = [annotation_hits[tag][0] for tag in tags]
    texts = [annotation_hits[tag][1] for tag in tags]
    sizes = [int(h.size) for h in hits]

    p_values, es, nes = gsea_p_values(scores, hits, n_permutations=n_permutations, p=weight_p, seed=seed)
    fdr = false_discovery_control(p_values, method="bh") if len(p_values) > 0 else np.array([])

    result = pd.DataFrame({
        "annotation_tag": tags,
        "text": texts,
        "size": sizes,
        "es": es,
        "nes": nes,
        "p_value": p_values,
        "fdr": fdr,
    })
    return result.sort_values("p_value").reset_index(drop=True)


def compute_annotation_gsea_series(
    annotation_hits: Dict[str, Tuple[np.ndarray, str]],
    ranked_rows: pd.DataFrame,
    annotation_tag: str,
    n_permutations: int = 1000,
    weight_p: float = 1.0,
    seed: int = 0,
) -> Optional[Dict]:
    """Running-sum series payload of one annotation for the GSEA plot.

    Returns the full running-sum series (one value per rank position), the hit
    ranks, the rank of the enrichment score peak, the leading-edge hit ranks,
    plus ES / NES / nominal p for the annotation. Leading edge convention:
    for a positive ES the hits up to the peak rank, for a negative ES the hits
    from the peak rank to the end of the list.
    """
    if annotation_tag not in annotation_hits or ranked_rows.empty:
        return None

    from services.gsea import gsea_p_values

    indices, text = annotation_hits[annotation_tag]
    scores = ranked_rows["log2fc"].to_numpy(dtype=np.float64)
    hit_mask = np.zeros(scores.size, dtype=bool)
    hit_mask[indices] = True
    es, running_sum = running_sum_enrichment_score(scores, hit_mask, p=weight_p)

    p_values, es_all, nes_all = gsea_p_values(
        scores, [indices], n_permutations=n_permutations, p=weight_p, seed=seed
    )

    es_rank = int(np.argmax(np.abs(running_sum)))
    if es >= 0:
        leading_edge = [int(i) for i in indices[indices <= es_rank]]
    else:
        leading_edge = [int(i) for i in indices[indices >= es_rank]]

    return {
        "annotation_tag": annotation_tag,
        "text": text,
        "size": int(indices.size),
        "leading_edge_size": len(leading_edge),
        "es": float(es),
        "nes": float(nes_all[0]),
        "p_value": float(p_values[0]),
        "es_rank": es_rank,
        "running_sum": [float(v) for v in running_sum],
        "hit_ranks": [int(i) for i in indices],
        "leading_edge_ranks": leading_edge,
    }

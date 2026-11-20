"""Enrichment analysis of annotations for a defined target protein list.

Pure statistics helpers, separated from the database layer so they can be
unit-tested without a graph database. The 2x2 contingency table per
annotation is:

                    in target list    not in target list
    annotated           a (target_count)      b
    not annotated       c                      d

with the universe restricted to ``universe_proteins`` (e.g. all proteins
quantified in a submission or all proteins of a proteome) and the target list
already intersected with that universe. Enrichment is tested one-sided
(Fisher exact, alternative="greater") and p-values are corrected with
Benjamini-Hochberg FDR.
"""
from typing import List, Optional

import numpy as np
import pandas as pd
from scipy.stats import fisher_exact, false_discovery_control

ENRICHMENT_COLUMNS = [
    "annotation_tag",
    "text",
    "target_with_annotation",
    "target_total",
    "universe_with_annotation",
    "universe_total",
    "odds_ratio",
    "p_value",
    "fdr",
]


def compute_annotation_enrichment(
    overlap_counts: pd.DataFrame,
    target_size: int,
    universe_size: int,
    min_overlap: int = 1,
) -> pd.DataFrame:
    """Computes one-sided Fisher exact enrichment per annotation plus BH FDR.

    Parameters
    ----------
    overlap_counts : pd.DataFrame
        DataFrame with columns ``annotation_tag``, ``text``, ``universe_count``
        (proteins of the annotation inside the universe) and ``target_count``
        (proteins of the annotation inside the target list).
    target_size : int
        Number of target proteins inside the universe.
    universe_size : int
        Number of proteins in the universe.
    min_overlap : int, optional
        Minimum number of target proteins annotated (``a``) for an annotation
        to be tested, by default 1.

    Returns
    -------
    pd.DataFrame
        One row per tested annotation, sorted by ascending p-value, with the
        columns of ``ENRICHMENT_COLUMNS``. ``odds_ratio`` is None where it is
        not finite (e.g. zero cells).
    """
    result = pd.DataFrame(columns=ENRICHMENT_COLUMNS)
    if overlap_counts is None or overlap_counts.empty:
        return result
    if target_size <= 0 or universe_size <= 0:
        return result

    df = overlap_counts.copy()
    df = df[df["target_count"] >= min_overlap]
    if df.empty:
        return result

    a = df["target_count"].to_numpy(dtype=float)
    universe_count = df["universe_count"].to_numpy(dtype=float)
    b = target_size - a
    c = universe_count - a
    d = universe_size - target_size - universe_count + a

    p_values = np.empty(len(df), dtype=float)
    odds_ratios = np.empty(len(df), dtype=float)
    for i in range(len(df)):
        odds, p = fisher_exact([[a[i], b[i]], [c[i], d[i]]], alternative="greater")
        odds_ratios[i] = odds
        p_values[i] = p

    fdr = false_discovery_control(p_values) if len(df) > 1 else p_values.copy()

    result = pd.DataFrame({
        "annotation_tag": df["annotation_tag"].to_numpy(),
        "text": df["text"].to_numpy() if "text" in df.columns else df["annotation_tag"].to_numpy(),
        "target_with_annotation": a.astype(int),
        "target_total": int(target_size),
        "universe_with_annotation": universe_count.astype(int),
        "universe_total": int(universe_size),
        "odds_ratio": odds_ratios,
        "p_value": p_values,
        "fdr": fdr,
    })
    result["odds_ratio"] = result["odds_ratio"].replace([np.inf, -np.inf], np.nan)
    result = result.sort_values("p_value").reset_index(drop=True)
    return result


def enrichment_records(result: pd.DataFrame, limit: Optional[int] = None) -> List[dict]:
    """Converts an enrichment result DataFrame to JSON-safe records (NaN -> None)."""
    if limit is not None:
        result = result.head(limit)
    return result.astype(object).where(pd.notna(result), None).to_dict(orient="records")

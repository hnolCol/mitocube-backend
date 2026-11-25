import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

SRC_DIR = Path(__file__).resolve().parent.parent.parent / "src"
sys.path.insert(0, str(SRC_DIR))

from services.annotations.gsea import (
    compute_annotation_gsea,
    compute_annotation_gsea_series,
    compute_annotation_hits_from_protein_map,
    filter_annotation_hits,
    prepare_ranked_rows,
)


def _ranked_rows(n_proteins=100):
    tags = [f"P{i}" for i in range(n_proteins)]
    stats = pd.DataFrame({
        "tag": [f"{t};" if False else t for t in tags],
        "tag_joined": tags,
        "log2FC suffix": np.linspace(5.0, -5.0, n_proteins),
    })
    return stats, tags


def test_prepare_ranked_rows_sorts_descending():
    stats = pd.DataFrame({
        "tag": ["P1", "P2;P3", "P4"],
        "log2FC suffix": [1.0, 3.0, np.nan],
    })
    ranked = prepare_ranked_rows(stats, "log2FC suffix")
    assert len(ranked) == 2
    assert ranked.iloc[0]["tag"] == "P2;P3"
    assert ranked.iloc[0]["protein_tags"] == ["P2", "P3"]
    assert ranked.iloc[1]["tag"] == "P1"
    assert ranked["log2fc"].is_monotonic_decreasing


def test_prepare_ranked_rows_empty():
    assert prepare_ranked_rows(pd.DataFrame(), "log2FC suffix").empty
    assert prepare_ranked_rows(pd.DataFrame({"tag": ["P1"]}), "missing").empty


def test_hits_map_proteins_to_ranked_rows():
    ranked = pd.DataFrame({
        "tag": ["P1;P2", "P3", "P4"],
        "protein_tags": [["P1", "P2"], ["P3"], ["P4"]],
        "log2fc": [3.0, 1.0, 0.5],
    })
    protein_map = pd.DataFrame({
        "annotation_tag": ["A1", "A2", "A3"],
        "text": ["term one", "term two", "term three"],
        "protein_tags": [["P1", "P3"], ["P9"], ["P2", "P4"]],
    })
    hits = compute_annotation_hits_from_protein_map(ranked, protein_map)
    assert set(hits.keys()) == {"A1", "A3"}
    np.testing.assert_array_equal(hits["A1"][0], [0, 1])
    np.testing.assert_array_equal(hits["A3"][0], [0, 2])


def test_filter_annotation_hits_size_band():
    hits = {
        "small": (np.arange(2), "small"),
        "mid": (np.arange(10), "mid"),
        "large": (np.arange(100), "large"),
    }
    filtered = filter_annotation_hits(hits, min_size=5, max_size=50)
    assert list(filtered.keys()) == ["mid"]


def test_compute_annotation_gsea_and_series():
    n = 300
    tags = [f"P{i}" for i in range(n)]
    stats = pd.DataFrame({
        "tag": tags,
        "log2FC suffix": np.linspace(10.0, -10.0, n),
    })
    ranked = prepare_ranked_rows(stats, "log2FC suffix")
    protein_map = pd.DataFrame({
        "annotation_tag": ["A_top", "A_bottom"],
        "text": ["top term", "bottom term"],
        "protein_tags": [tags[:20], tags[-20:]],
    })
    hits = compute_annotation_hits_from_protein_map(ranked, protein_map)
    hits = filter_annotation_hits(hits, min_size=5)

    table = compute_annotation_gsea(hits, ranked, n_permutations=200, seed=1)
    assert set(table.columns) == {"annotation_tag", "text", "size", "es", "nes", "p_value", "fdr"}
    top = table[table["annotation_tag"] == "A_top"].iloc[0]
    bottom = table[table["annotation_tag"] == "A_bottom"].iloc[0]
    assert top["es"] > 0.9
    assert bottom["es"] < -0.5
    assert top["p_value"] < 0.05
    assert np.all((table["p_value"] >= 0) & (table["p_value"] <= 1))
    assert np.all((table["fdr"] >= 0) & (table["fdr"] <= 1))

    series = compute_annotation_gsea_series(hits, ranked, "A_top", n_permutations=200, seed=1)
    assert series is not None
    assert len(series["running_sum"]) == n
    assert series["size"] == 20
    assert series["es"] > 0.9
    assert series["leading_edge_size"] > 0
    assert all(0 <= rank < n for rank in series["hit_ranks"])
    assert series["leading_edge_ranks"] == [r for r in series["hit_ranks"] if r <= series["es_rank"]]
    assert compute_annotation_gsea_series(hits, ranked, "missing", n_permutations=20) is None


def test_compute_annotation_gsea_series_negative_es_leading_edge():
    n = 300
    tags = [f"P{i}" for i in range(n)]
    stats = pd.DataFrame({"tag": tags, "log2FC suffix": np.linspace(10.0, -10.0, n)})
    ranked = prepare_ranked_rows(stats, "log2FC suffix")
    protein_map = pd.DataFrame({
        "annotation_tag": ["A_bottom"],
        "text": ["bottom term"],
        "protein_tags": [tags[-20:]],
    })
    hits = compute_annotation_hits_from_protein_map(ranked, protein_map)
    series = compute_annotation_gsea_series(hits, ranked, "A_bottom", n_permutations=100, seed=2)
    assert series["es"] < 0
    assert series["leading_edge_ranks"] == [r for r in series["hit_ranks"] if r >= series["es_rank"]]

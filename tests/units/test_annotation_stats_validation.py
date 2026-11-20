"""Statistical validation of the annotation enrichment (Fisher) and shift (U-test)
helpers against independent references:

- Fisher one-sided p-values are cross-checked against scipy's fisher_exact AND
  against the equivalent hypergeometric survival function
  P(X >= a) with X ~ Hypergeom(M=universe, n=annotated in universe, N=target).
- Mann-Whitney U p-values are cross-checked against scipy's mannwhitneyu, and the
  tag-based and member-values-based shift implementations must agree exactly.
- Benjamini-Hochberg FDR is validated against the manual BH formula, and the 2x2
  table invariants (a+b = target, a+c = annotated, a+b+c+d = universe) must hold.
"""
import numpy as np
import pandas as pd
import pytest
from scipy.stats import fisher_exact, mannwhitneyu, hypergeom, false_discovery_control

from services.annotations.enrichment import (
    compute_annotation_enrichment,
    compute_annotation_shift,
    compute_annotation_shift_from_member_values,
)


def bh_reference(p_values):
    """Manual Benjamini-Hochberg: q_i = min_{j >= i} (p_j * m / j) over sorted p."""
    p = np.sort(np.asarray(p_values, dtype=float))
    m = len(p)
    if m == 0:
        return p
    ranks = np.arange(1, m + 1)
    q = p * m / ranks
    return np.minimum.accumulate(q[::-1])[::-1]


# ---------------------------------------------------------------------------
# Fisher / overrepresentation
# ---------------------------------------------------------------------------

def test_fisher_pvalues_match_scipy_and_hypergeom_random_tables():
    rng = np.random.default_rng(42)
    for _ in range(200):
        universe_size = int(rng.integers(20, 500))
        target_size = int(rng.integers(2, max(3, universe_size // 2)))
        universe_count = int(rng.integers(1, universe_size))
        lo = max(0, target_size + universe_count - universe_size)
        target_count = int(rng.integers(lo, min(target_size, universe_count) + 1))
        overlap = pd.DataFrame({
            "annotation_tag": ["ann"],
            "text": ["t"],
            "universe_count": [universe_count],
            "target_count": [target_count],
        })
        result = compute_annotation_enrichment(overlap, target_size, universe_size, min_overlap=0)
        assert len(result) == 1
        row = result.iloc[0]

        a, b = target_count, target_size - target_count
        c, d = universe_count - target_count, universe_size - target_size - universe_count + target_count
        # 2x2 table invariants
        assert a + b == target_size == row["target_total"]
        assert a + c == universe_count == row["universe_with_annotation"]
        assert a + b + c + d == universe_size == row["universe_total"]

        _, p_fisher = fisher_exact([[a, b], [c, d]], alternative="greater")
        p_hyper = float(hypergeom.sf(a - 1, universe_size, universe_count, target_size))
        assert row["p_value"] == pytest.approx(p_fisher, rel=1e-12, abs=1e-300)
        assert row["p_value"] == pytest.approx(p_hyper, rel=1e-9, abs=1e-300)
        odds_fisher, _ = fisher_exact([[a, b], [c, d]], alternative="greater")
        if np.isfinite(odds_fisher):
            assert row["odds_ratio"] == pytest.approx(odds_fisher)


def test_fisher_fdr_matches_manual_bh_and_is_valid():
    rng = np.random.default_rng(7)
    rows = []
    for i in range(50):
        universe_size, target_size = 200, 20
        universe_count = int(rng.integers(5, 100))
        lo = max(0, target_size + universe_count - universe_size)
        target_count = int(rng.integers(lo, min(target_size, universe_count) + 1))
        rows.append({"annotation_tag": f"ann_{i}", "text": f"t{i}",
                     "universe_count": universe_count, "target_count": target_count})
    overlap = pd.DataFrame(rows)
    result = compute_annotation_enrichment(overlap, 20, 200, min_overlap=1)
    p_sorted = result["p_value"].to_numpy()
    assert np.all(np.diff(p_sorted) >= -1e-15)  # sorted by p-value
    expected_q = bh_reference(p_sorted)
    assert np.allclose(np.sort(result["fdr"].to_numpy()), np.sort(expected_q), rtol=1e-9)
    assert np.all(result["fdr"].to_numpy() >= p_sorted - 1e-12)  # FDR never below p
    # scipy false_discovery_control (BH) must agree with our fdr column
    assert np.allclose(result["fdr"].to_numpy(), false_discovery_control(p_sorted), rtol=1e-9)


def test_fisher_perfect_overlap_gives_extreme_pvalue():
    # target list == exactly the annotation members: a = target = universe_count
    overlap = pd.DataFrame({
        "annotation_tag": ["ann"], "text": ["t"], "universe_count": [10], "target_count": [10],
    })
    result = compute_annotation_enrichment(overlap, target_size=10, universe_size=100)
    assert result.iloc[0]["p_value"] == pytest.approx(hypergeom.sf(9, 100, 10, 10))
    assert result.iloc[0]["p_value"] < 1e-10
    assert result.iloc[0]["odds_ratio"] is None or not np.isfinite(result.iloc[0]["odds_ratio"])  # c=0 -> inf -> null in records


# ---------------------------------------------------------------------------
# Mann-Whitney U / systematic shift
# ---------------------------------------------------------------------------

def test_shift_matches_mannwhitneyu_and_tag_based_variant_random():
    rng = np.random.default_rng(123)
    for _ in range(100):
        n = int(rng.integers(20, 200))
        universe = [f"p{i}" for i in range(n)]
        shift = float(rng.normal(0, 3))
        values = {p: float(rng.normal(shift if i < n // 4 else 0.0, 1.0)) for i, p in enumerate(universe)}
        members = universe[: n // 4]
        members_df = pd.DataFrame({
            "annotation_tag": ["ann"], "text": ["t"], "protein_tags": [members],
        })
        member_values_df = pd.DataFrame({
            "annotation_tag": ["ann"], "text": ["t"],
            "member_values": [[values[p] for p in members]],
        })
        result_tags = compute_annotation_shift(values, members_df, min_size=3)
        result_vals = compute_annotation_shift_from_member_values(values, member_values_df, min_size=3)
        assert len(result_tags) == len(result_vals) == 1
        rt, rv = result_tags.iloc[0], result_vals.iloc[0]
        # both implementations must agree exactly
        assert rt["direction"] == rv["direction"]
        for col in ["p_value", "u_statistic", "n_in", "n_out", "mean_in", "mean_out", "shift"]:
            assert rt[col] == pytest.approx(rv[col], rel=1e-9, abs=1e-12), col
        # n_out = universe with values minus annotation members
        assert rv["n_out"] == len(values) - rv["n_in"]
        # direct scipy reference
        out_vals = np.array([v for k, v in values.items() if k not in set(members)])
        in_vals = np.array([values[p] for p in members])
        u_ref, p_ref = mannwhitneyu(in_vals, out_vals, alternative="two-sided")
        assert rv["p_value"] == pytest.approx(p_ref, rel=1e-12)
        assert rv["u_statistic"] == pytest.approx(u_ref, rel=1e-9)
        expected_dir = "up" if in_vals.mean() >= out_vals.mean() else "down"
        assert rv["direction"] == expected_dir
        assert rv["shift"] == pytest.approx(in_vals.mean() - out_vals.mean())


def test_shift_constant_values_give_pvalue_one():
    values = {f"p{i}": 1.0 for i in range(30)}
    members_df = pd.DataFrame({
        "annotation_tag": ["ann"], "text": ["t"], "protein_tags": [[f"p{i}" for i in range(10)]],
    })
    result = compute_annotation_shift(values, members_df, min_size=3)
    assert result.iloc[0]["p_value"] == pytest.approx(1.0)
    assert result.iloc[0]["direction"] == "up"  # mean_in >= mean_out (equal)


def test_shift_fdr_properties_random():
    rng = np.random.default_rng(99)
    n = 150
    universe = [f"p{i}" for i in range(n)]
    values = {p: float(rng.normal(0, 1)) for p in universe}
    rows = []
    for i in range(30):
        members = list(rng.choice(universe, size=int(rng.integers(5, 30)), replace=False))
        rows.append({"annotation_tag": f"ann_{i}", "text": f"t{i}", "protein_tags": members})
    result = compute_annotation_shift(values, pd.DataFrame(rows), min_size=3)
    p_sorted = result["p_value"].to_numpy()
    assert np.all(np.diff(p_sorted) >= -1e-15)
    assert np.allclose(np.sort(result["fdr"].to_numpy()), np.sort(bh_reference(p_sorted)), rtol=1e-9)
    assert np.all(result["fdr"].to_numpy() >= p_sorted - 1e-12)

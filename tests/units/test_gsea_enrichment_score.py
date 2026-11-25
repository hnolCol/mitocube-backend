import sys
from pathlib import Path

import numpy as np
import pytest

SRC_DIR = Path(__file__).resolve().parent.parent.parent / "src"
sys.path.insert(0, str(SRC_DIR))

from services.gsea import (
    enrichment_scores,
    gsea_p_values,
    null_enrichment_scores,
    running_sum_enrichment_score,
)


def _naive_es(scores, hit_mask, p=1.0):
    scores = np.asarray(scores, dtype=float)
    hit_mask = np.asarray(hit_mask, dtype=bool)
    n = scores.size
    n_h = int(hit_mask.sum())
    if n_h == 0:
        return 0.0
    weights = np.abs(scores) ** p
    hit_sum = weights[hit_mask].sum()
    miss_step = 1.0 / (n - n_h) if n_h < n else 1.0
    running = 0.0
    best = 0.0
    hit_seen = 0.0
    for i in range(n):
        if hit_mask[i]:
            running += weights[i] / hit_sum
        elif n_h < n:
            running -= miss_step
        if abs(running) > abs(best):
            best = running
    return best


def _naive_es_series(scores, hit_mask, p=1.0):
    scores = np.asarray(scores, dtype=float)
    hit_mask = np.asarray(hit_mask, dtype=bool)
    n = scores.size
    n_h = int(hit_mask.sum())
    if n_h == 0:
        return np.zeros(n)
    weights = np.abs(scores) ** p
    hit_sum = weights[hit_mask].sum()
    miss_step = 1.0 / (n - n_h) if n_h < n else 0.0
    out = np.empty(n)
    running = 0.0
    for i in range(n):
        if hit_mask[i]:
            running += weights[i] / hit_sum
        elif n_h < n:
            running -= miss_step
        out[i] = running
    return out


@pytest.mark.parametrize("seed", [0, 1, 2, 3, 4])
@pytest.mark.parametrize("n", [10, 50, 137])
@pytest.mark.parametrize("n_h", [1, 3, 10, None])
def test_single_set_matches_naive(seed, n, n_h):
    rng = np.random.default_rng(seed)
    scores = np.sort(rng.normal(size=n).astype(np.float64))[::-1]
    if n_h is None:
        n_h = int(rng.integers(1, n))
    n_h = min(n_h, n)
    hit_idx = rng.choice(n, size=n_h, replace=False)
    hit_mask = np.zeros(n, dtype=bool)
    hit_mask[hit_idx] = True

    expected = _naive_es(scores, hit_mask)
    es, rs = running_sum_enrichment_score(scores, hit_mask)

    assert es == pytest.approx(expected, abs=1e-12)
    np.testing.assert_allclose(rs, _naive_es_series(scores, hit_mask), atol=1e-12)


@pytest.mark.parametrize("seed", [0, 1, 2])
@pytest.mark.parametrize("n", [30, 200])
def test_batched_matches_single(seed, n):
    rng = np.random.default_rng(seed)
    scores = np.sort(rng.normal(size=n).astype(np.float64))[::-1]

    sets = []
    expected = []
    for _ in range(25):
        n_h = int(rng.integers(1, n + 1))
        hit_idx = rng.choice(n, size=n_h, replace=False)
        mask = np.zeros(n, dtype=bool)
        mask[hit_idx] = True
        sets.append(hit_idx)
        expected.append(_naive_es(scores, mask))

    got = enrichment_scores(scores, np.array(sets, dtype=object), p=1.0)
    np.testing.assert_allclose(got, expected, atol=1e-12)


@pytest.mark.parametrize("n_h", [0, 1, 5])
def test_edge_cases(n_h):
    rng = np.random.default_rng(0)
    n = 20
    scores = np.sort(rng.normal(size=n).astype(np.float64))[::-1]
    hit_idx = np.arange(n_h)
    mask = np.zeros(n, dtype=bool)
    mask[hit_idx] = True

    es_single, rs = running_sum_enrichment_score(scores, mask)
    es_batch = enrichment_scores(scores, hit_idx[None, :])[0]
    assert es_single == pytest.approx(es_batch, abs=1e-12)
    assert es_single == pytest.approx(_naive_es(scores, mask), abs=1e-12)


def test_full_and_empty_sets():
    scores = np.linspace(3.0, 0.1, 10)
    all_mask = np.ones(10, dtype=bool)
    es, _ = running_sum_enrichment_score(scores, all_mask)
    assert es == pytest.approx(1.0)

    none_mask = np.zeros(10, dtype=bool)
    es, rs = running_sum_enrichment_score(scores, none_mask)
    assert es == 0.0
    assert np.all(rs == 0.0)

    assert enrichment_scores(scores, np.empty((3, 0), dtype=np.int64)).shape == (3,)


def test_enriched_set_gets_positive_es():
    scores = np.linspace(10.0, 0.0, 100)
    hit_mask = np.zeros(100, dtype=bool)
    hit_mask[:10] = True
    es, rs = running_sum_enrichment_score(scores, hit_mask)
    assert es > 0.9
    assert int(np.argmax(rs)) < 10


def test_depleted_set_gets_negative_es():
    scores = np.linspace(10.0, 0.0, 100)
    hit_mask = np.zeros(100, dtype=bool)
    hit_mask[-10:] = True
    es, rs = running_sum_enrichment_score(scores, hit_mask)
    assert es < -0.5


def test_null_distribution_centred_near_zero():
    rng = np.random.default_rng(7)
    n = 500
    scores = np.sort(rng.normal(size=n).astype(np.float64))[::-1]
    null = null_enrichment_scores(scores, 20, 500, seed=7)
    assert null.shape == (500,)
    assert null.mean() > -0.5
    assert null.std() > 0.1
    assert (null.max() < 1.0) and (null.min() > -1.0)


def test_null_reproducible_with_seed():
    scores = np.linspace(5.0, 0.5, 300)
    a = null_enrichment_scores(scores, 15, 50, seed=42)
    b = null_enrichment_scores(scores, 15, 50, seed=42)
    np.testing.assert_array_equal(a, b)


def test_gsea_p_values_enriched_vs_random():
    rng = np.random.default_rng(5)
    scores = np.linspace(10.0, 0.0, 300)
    enriched = np.arange(10)
    scattered = np.sort(rng.choice(300, size=40, replace=False))
    p, es, nes = gsea_p_values(scores, [enriched, scattered], n_permutations=300, seed=1)
    assert nes[0] > 0
    assert np.sign(nes[1]) == np.sign(es[1])
    assert es[0] > 0.9
    assert p[0] < 0.05
    assert p[1] > p[0]
    assert np.all((p >= 0) & (p <= 1))


def test_gsea_p_values_ragged_sizes():
    rng = np.random.default_rng(3)
    scores = np.sort(rng.normal(size=400).astype(np.float64))[::-1]
    sets = [
        np.sort(rng.choice(400, size=8, replace=False)),
        np.sort(rng.choice(400, size=30, replace=False)),
        np.sort(rng.choice(400, size=8, replace=False)),
    ]
    p, es, _ = gsea_p_values(scores, sets, n_permutations=100, seed=2)
    assert p.shape == (3,)
    assert es.shape == (3,)
    np.testing.assert_allclose(es, enrichment_scores(scores, sets))


def test_gsea_p_values_from_constant_ranked_list_are_reproducible():
    scores = np.linspace(2.0, 0.2, 250)
    sets = [np.arange(0, 40, 4), np.arange(100, 140, 4)]
    p1, _, nes1 = gsea_p_values(scores, sets, n_permutations=50, seed=9)
    p2, _, nes2 = gsea_p_values(scores, sets, n_permutations=50, seed=9)
    np.testing.assert_allclose(nes1, nes2)
    np.testing.assert_allclose(p1, p2)

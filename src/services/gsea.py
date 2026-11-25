import numpy as np


def running_sum_enrichment_score(scores, hit_mask, p=1.0):
    """O(N) single-set GSEA enrichment score (weighted Kolmogorov-Smirnov).

    `scores` must be sorted descending (highest ranked first). `hit_mask` is a
    boolean array marking set members in the ranked list. Returns
    (ES, running_sum_series) with one running-sum value per rank position.
    """
    scores = np.asarray(scores, dtype=np.float64)
    hit_mask = np.asarray(hit_mask, dtype=bool)
    n = scores.size
    n_h = int(hit_mask.sum())

    rs = np.zeros(n, dtype=np.float64)
    if n_h == 0:
        return 0.0, rs
    if n_h == n:
        np.cumsum(np.abs(scores) ** p, out=rs)
        return 1.0, rs / rs[-1]

    weights = np.abs(scores) ** p
    hit_weights = weights[hit_mask]
    hit_increments = hit_weights / hit_weights.sum()
    miss_step = 1.0 / (n - n_h)

    increments = np.where(hit_mask, 0.0, -miss_step)
    increments[hit_mask] = hit_increments
    np.cumsum(increments, out=rs)

    max_i = int(np.argmax(rs))
    min_i = int(np.argmin(rs))
    es = float(rs[max_i] if rs[max_i] >= -rs[min_i] else rs[min_i])
    return es, rs


def _enrichment_scores_uniform(scores, hits, p):
    """Vectorized ES for many hits arrays that share the same set size."""
    hits = np.sort(np.ascontiguousarray(hits, dtype=np.int64), axis=1)
    n_sets, n_h = hits.shape
    n = scores.size

    weights = np.abs(scores) ** p
    hit_w = weights[hits]
    hit_w = hit_w / hit_w.sum(axis=1, keepdims=True)
    cw = np.cumsum(hit_w, axis=1)

    miss_step = 1.0 / (n - n_h)
    misses_before = hits - np.arange(n_h)[None, :]
    rs_at_hits = cw - misses_before * miss_step

    minima_candidates = [
        rs_at_hits[:, -1] - (n - 1 - hits[:, -1]) * miss_step,
        -hits[:, 0] * miss_step,
    ]
    if n_h > 1:
        gaps = hits[:, 1:] - hits[:, :-1] - 1
        minima_candidates.append(
            (rs_at_hits[:, :-1] - gaps * miss_step).min(axis=1)
        )

    maxima = np.maximum(rs_at_hits.max(axis=1), 0.0)
    minima = np.minimum(np.minimum.reduce(minima_candidates), 0.0)
    return np.where(maxima >= -minima, maxima, minima)


def enrichment_scores(scores, hits, p=1.0):
    """Batched enrichment scores for many sets sharing one ranked list.

    `scores`: 1-D array sorted descending. `hits`: either a 2-D int array
    (n_sets, n_h) of hit positions in the ranked list (unsorted allowed), or
    a list / ragged object array of 1-D index arrays with varying set sizes.
    Weights are normalized per set on its own hit positions, matching
    gene-set permutation semantics (GSEA prerank style).
    """
    scores = np.asarray(scores, dtype=np.float64)
    n = scores.size

    if isinstance(hits, np.ndarray) and hits.ndim == 2 and hits.dtype != object:
        index_arrays = list(hits.reshape(len(hits), -1))
    else:
        index_arrays = [np.asarray(h, dtype=np.int64).ravel() for h in hits]

    if not index_arrays:
        return np.zeros(0, dtype=np.float64)

    n_sets = len(index_arrays)
    out = np.empty(n_sets, dtype=np.float64)
    done = np.zeros(n_sets, dtype=bool)

    by_len = {}
    for i, arr in enumerate(index_arrays):
        by_len.setdefault(arr.size, []).append(i)

    for size, indices in by_len.items():
        if size == 0 or size >= n:
            out[indices] = 1.0 if size == n and n > 0 else 0.0
            continue
        batch = np.stack([index_arrays[i] for i in indices])
        out[indices] = _enrichment_scores_uniform(scores, batch, p)

    return out


def null_enrichment_scores(scores, n_h, n_permutations, p=1.0, seed=None):
    """Monte Carlo null ES distribution for random sets of size n_h."""
    scores = np.asarray(scores, dtype=np.float64)
    n = scores.size
    rng = np.random.default_rng(seed)

    if n_h == 0:
        return np.zeros(n_permutations, dtype=np.float64)
    if n_h == n:
        return np.ones(n_permutations, dtype=np.float64)
    if n_h > n:
        raise ValueError("Set size larger than the ranked list.")

    hits = np.empty((n_permutations, n_h), dtype=np.int64)
    for i in range(n_permutations):
        hits[i] = rng.choice(n, n_h, replace=False)
    return _enrichment_scores_uniform(scores, hits, p)


_NULL_CACHE = {}


def _cached_null_scores(scores_tag, scores, n_h, n_permutations, p, seed):
    key = (scores_tag, n_h, n_permutations, p, seed)
    cached = _NULL_CACHE.get(key)
    if cached is None:
        cached = null_enrichment_scores(scores, n_h, n_permutations, p=p, seed=seed)
        if len(_NULL_CACHE) > 128:
            _NULL_CACHE.clear()
        _NULL_CACHE[key] = cached
    return cached


def gsea_p_values(scores, hits, n_permutations=1000, p=1.0, seed=0):
    """GSEA-style nominal p-values for many annotations against one ranked list.

    Because the gene-set-permutation null depends only on the ranked list and
    the set size (not set membership), one null distribution is shared by all
    annotations of the same size. Nominal p-values use the classic same-sign
    convention: fraction of null ES values at least as extreme as the
    observed ES with the same sign. Returns (p_values, es_scores).
    """
    scores = np.asarray(scores, dtype=np.float64)
    es = enrichment_scores(scores, hits, p=p)

    index_arrays = [np.asarray(h, dtype=np.int64).ravel() for h in hits] \
        if not (isinstance(hits, np.ndarray) and hits.ndim == 2 and hits.dtype != object) \
        else list(hits.reshape(len(hits), -1))
    sizes = [arr.size for arr in index_arrays]

    p_values = np.ones(len(es), dtype=np.float64)
    by_size = {}
    for i, size in enumerate(sizes):
        by_size.setdefault(size, []).append(i)

    scores_tag = (scores.shape[0], hash(scores.tobytes()), float(scores[0]) if scores.size else 0.0)
    for size, indices in by_size.items():
        null = _cached_null_scores(scores_tag, scores, size, n_permutations, p, seed)
        obs = es[indices]
        pos = obs >= 0
        denom = max(1, int((null >= 0).sum()))
        denom_neg = max(1, int((null < 0).sum()))
        pos_null = null[null >= 0]
        neg_null = null[null < 0]
        for row_local, i in enumerate(indices):
            if pos[row_local]:
                p_values[i] = np.sum(pos_null >= obs[row_local]) / denom
            else:
                p_values[i] = np.sum(neg_null <= obs[row_local]) / denom_neg
    return p_values, es

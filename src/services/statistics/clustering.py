import numpy as np
from numba import njit
import pandas as pd

@njit(cache=True)
def pairwise_euclidean(X):
    """
    Compute full n x n Euclidean distance matrix, NaN-aware.
    Distance between rows i, j is computed only over dimensions where
    both rows have non-NaN values, then scaled back up to full dimensionality
    (average squared diff * n_features) so distances stay comparable across
    pairs with different amounts of missingness.
    If two rows share zero overlapping non-NaN dimensions, distance is inf
    (they should never be merged based on no shared evidence).
    """
    n = X.shape[0]
    n_features = X.shape[1]
    D = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            s = 0.0
            count = 0
            for k in range(n_features):
                a = X[i, k]
                b = X[j, k]
                if not np.isnan(a) and not np.isnan(b):
                    diff = a - b
                    s += diff * diff
                    count += 1
            if count == 0:
                d = np.inf
            else:
                # mean squared diff over overlapping dims, rescaled to full dim count
                d = np.sqrt((s / count) * n_features)
            D[i, j] = d
            D[j, i] = d
    return D

def filter_for_clustering(df, min_valid_per_row=None):
    """Drop rows too sparse to reliably cluster."""
    if min_valid_per_row is None:
        min_valid_per_row = max(3, df.shape[1] // 2)  # e.g. at least half the samples
    valid_counts = df.notna().sum(axis=1)
    return df.loc[valid_counts >= min_valid_per_row]


@njit(cache=True)
def complete_linkage(D, n_clusters):
    """
    Agglomerative complete-linkage clustering on a precomputed distance matrix.
    Returns a 1D array of cluster labels (0..n_clusters-1).
    """
    n = D.shape[0]
    D = D.copy()
    active = np.ones(n, dtype=np.bool_)
    labels = np.arange(n)
    n_active = n

    while n_active > n_clusters:
        # find closest pair among active clusters
        best_dist = np.inf
        bi, bj = -1, -1
        for i in range(n):
            if not active[i]:
                continue
            for j in range(i + 1, n):
                if not active[j]:
                    continue
                if D[i, j] < best_dist:
                    best_dist = D[i, j]
                    bi, bj = i, j

        # merge cluster bj into bi (complete linkage: max distance)
        for k in range(n):
            if active[k] and k != bi and k != bj:
                D[bi, k] = max(D[bi, k], D[bj, k])
                D[k, bi] = D[bi, k]

        active[bj] = False
        old_label = labels[bj]
        new_label = labels[bi]
        for k in range(n):
            if labels[k] == old_label:
                labels[k] = new_label

        n_active -= 1

    # relabel to 0..n_clusters-1
    out = np.full(n, -1)
    next_id = 0
    for i in range(n):
        if out[i] == -1:
            lbl = labels[i]
            for k in range(n):
                if labels[k] == lbl:
                    out[k] = next_id
            next_id += 1
    return out


def cluster(X, n_clusters):
    """Convenience wrapper: X is (n_samples, n_features) numpy array."""
    D = pairwise_euclidean(np.ascontiguousarray(X, dtype=np.float64))
    return complete_linkage(D, n_clusters)


def silhouette_from_D(D, labels):
    """
    Silhouette score using a precomputed distance matrix.
    Avoids depending on sklearn; O(n^2), fine for the same scale as clustering itself.
    """
    n = D.shape[0]
    unique_labels = np.unique(labels)
    if len(unique_labels) < 2 or len(unique_labels) >= n:
        return -1.0  # undefined / degenerate

    s = np.zeros(n)
    for i in range(n):
        own = labels[i]
        mask_own = (labels == own)
        n_own = mask_own.sum() - 1
        a = D[i, mask_own].sum() / n_own if n_own > 0 else 0.0

        b = np.inf
        for lbl in unique_labels:
            if lbl == own:
                continue
            mask_other = (labels == lbl)
            mean_dist = D[i, mask_other].mean()
            if mean_dist < b:
                b = mean_dist

        s[i] = (b - a) / max(a, b) if max(a, b) > 0 else 0.0

    return s.mean()


def find_best_k(X, k_range):
    """
    Try each k in k_range, return (best_k, scores_dict).
    Reuses the same distance matrix across all k values for efficiency.
    """
    D = pairwise_euclidean(np.ascontiguousarray(X, dtype=np.float64))
    scores = {}
    for k in k_range:
        labels = complete_linkage(D, k)
        scores[k] = silhouette_from_D(D, labels)
    best_k = max(scores, key=scores.get)
    return best_k, scores

@njit(cache=True)
def pairwise_euclidean(X):
    """
    Compute full n x n Euclidean distance matrix, NaN-aware.
    Distance between rows i, j is computed only over dimensions where
    both rows have non-NaN values, then scaled back up to full dimensionality
    (average squared diff * n_features) so distances stay comparable across
    pairs with different amounts of missingness.
    If two rows share zero overlapping non-NaN dimensions, distance is inf
    (they should never be merged based on no shared evidence).
    """
    n = X.shape[0]
    n_features = X.shape[1]
    D = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            s = 0.0
            count = 0
            for k in range(n_features):
                a = X[i, k]
                b = X[j, k]
                if not np.isnan(a) and not np.isnan(b):
                    diff = a - b
                    s += diff * diff
                    count += 1
            if count == 0:
                d = np.inf
            else:
                # mean squared diff over overlapping dims, rescaled to full dim count
                d = np.sqrt((s / count) * n_features)
            D[i, j] = d
            D[j, i] = d
    return D

@njit(cache=True)
def complete_linkage_history(D):
    n = D.shape[0]
    D = D.copy()
    active = np.ones(n, dtype=np.bool_)

    merge_bi = np.zeros(n - 1, dtype=np.int64)
    merge_bj = np.zeros(n - 1, dtype=np.int64)
    merge_dist = np.zeros(n - 1)

    for step in range(n - 1):
        best_dist = np.inf
        bi, bj = -1, -1
        for i in range(n):
            if not active[i]:
                continue
            for j in range(i + 1, n):
                if not active[j]:
                    continue
                if D[i, j] < best_dist:
                    best_dist = D[i, j]
                    bi, bj = i, j

        if bi == -1:
            # no finite distance left between any active pair
            raise Exception("No valid pair to merge - check for rows with no overlapping non-NaN features.")

        for k in range(n):
            if active[k] and k != bi and k != bj:
                D[bi, k] = max(D[bi, k], D[bj, k])
                D[k, bi] = D[bi, k]

        active[bj] = False
        merge_bi[step] = bi
        merge_bj[step] = bj
        merge_dist[step] = best_dist

    return merge_bi, merge_bj, merge_dist


def labels_from_history(merge_bi, merge_bj, n, n_clusters):
    """Cut the dendrogram at n_clusters by replaying the first (n - n_clusters) merges."""
    labels = np.arange(n)
    n_merges = n - n_clusters
    for step in range(n_merges):
        bi, bj = merge_bi[step], merge_bj[step]
        old_label, new_label = labels[bj], labels[bi]
        labels[labels == old_label] = new_label

    out = np.full(n, -1)
    next_id = 0
    for lbl in np.unique(labels):
        out[labels == lbl] = next_id
        next_id += 1
    return out


def leaf_order_from_history(merge_bi, merge_bj, n):
    """
    Reconstruct a dendrogram-consistent leaf order: proteins merged
    early (i.e. more similar) end up adjacent, nested groups stay contiguous.
    """
    leaves_at = {i: [i] for i in range(n)}
    root = None
    for bi, bj in zip(merge_bi, merge_bj):
        leaves_at[bi] = leaves_at[bi] + leaves_at.pop(bj)
        root = bi
    return leaves_at[root]


def cluster_to_dataframe(X, n_clusters, index=None, columns=None):
    X_arr = np.asarray(X, dtype=np.float64)
    n = X_arr.shape[0]
    D = pairwise_euclidean(np.ascontiguousarray(X_arr))

    merge_bi, merge_bj, merge_dist = complete_linkage_history(D)

    if np.any(merge_bi == -1) or np.any(merge_bj == -1):
        raise ValueError(
            "Clustering failed: some rows have no overlapping non-NaN features "
            "with any other row, so a valid merge could not be found."
        )

    labels = labels_from_history(merge_bi, merge_bj, n, n_clusters)
    order = leaf_order_from_history(merge_bi, merge_bj, n)

    df = pd.DataFrame(X_arr, index=index, columns=columns)
    df["cluster"] = labels
    return df.iloc[order]

    
    
    
def compute_zscores(df: pd.DataFrame) -> pd.DataFrame:
    """Row-wise (per-feature) z-scores, NaN-safe."""
    arr = df.values.astype(np.float64)
    mean = np.nanmean(arr, axis=1, keepdims=True)
    std = np.nanstd(arr, axis=1, keepdims=True)
    with np.errstate(invalid="ignore", divide="ignore"):
        z = (arr - mean) / std
    return pd.DataFrame(z, index=df.index, columns=df.columns)




if __name__ == "__main__":
    np.random.seed(0)
    X = np.vstack([
        np.random.randn(20, 2) + [0, 0],
        np.random.randn(20, 2) + [8, 8],
        np.random.randn(20, 2) + [0, 8],
    ])

    labels = cluster(X, n_clusters=3)
    print(labels)

    best_k, scores = find_best_k(X, k_range=range(2, 8))
    print("Silhouette scores:", scores)
    print("Best k:", best_k)

    df = cluster_to_dataframe(
        X, n_clusters=3,
        index=[f"protein_{i}" for i in range(X.shape[0])],
        columns=[f"sample_{j}" for j in range(X.shape[1])],
    )
    print(df.head())
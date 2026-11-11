import json

import numpy as np
import pandas as pd

from services.statistics.clustering import compute_zscores


def test_compute_zscores_is_finite_and_json_safe():
    df = pd.DataFrame(
        [
            [5.0, 5.0, 5.0, 5.0],
            [1.0, 2.0, np.nan, 4.0],
        ],
        index=["constant", "normal"],
        columns=["s1", "s2", "s3", "s4"],
    )
    z = compute_zscores(df)

    assert not np.isinf(z.values).any()
    assert z.loc["constant"].isna().all()
    assert z.loc["normal"].notna().sum() == 3

    records = (
        z.replace([np.inf, -np.inf], np.nan)
        .astype(object)
        .where(z.notna(), None)
        .reset_index(names="tag")
        .to_dict(orient="records")
    )
    json.dumps(records, allow_nan=False)


def test_cluster_to_dataframe_handles_disjoint_nan_rows():
    from services.statistics.clustering import cluster_to_dataframe

    # rows with disjoint non-NaN halves -> zero overlapping features between groups
    X = np.full((6, 8), np.nan)
    X[0, :4] = [1.0, 2.0, 1.5, 2.5]
    X[1, :4] = [1.1, 2.1, 1.4, 2.4]
    X[2, :4] = [5.0, 6.0, 5.5, 6.5]
    X[3, 4:] = [1.0, 2.0, 1.5, 2.5]
    X[4, 4:] = [1.2, 2.2, 1.3, 2.3]
    X[5, 4:] = [8.0, 9.0, 8.5, 9.5]

    df = cluster_to_dataframe(
        X, n_clusters=3,
        index=[f"p{i}" for i in range(X.shape[0])],
        columns=[f"s{j}" for j in range(X.shape[1])],
    )

    assert df.shape[0] == 6
    assert set(df["cluster"]) <= {0, 1, 2}
    assert set(df.index) == {f"p{i}" for i in range(6)}


def test_cluster_to_dataframe_single_row():
    from services.statistics.clustering import cluster_to_dataframe

    df = cluster_to_dataframe(
        np.array([[1.0, 2.0, np.nan]]), n_clusters=1,
        index=["only"], columns=["a", "b", "c"],
    )
    assert df.loc["only", "cluster"] == 0

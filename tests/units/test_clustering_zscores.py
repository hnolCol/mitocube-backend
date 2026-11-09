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

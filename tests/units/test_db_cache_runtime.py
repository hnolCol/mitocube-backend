from datetime import timedelta

import numpy as np
import pandas as pd

from lib.cache.cache import DBCacheRuntime


class FakeCollection:
    def __init__(self):
        self.docs = {}

    def find_one(self, query):
        return self.docs.get(query["cache_key"])

    def find_one_and_update(self, query, update, upsert=False, **kwargs):
        self.docs[query["cache_key"]] = {"cache_key": query["cache_key"], **update["$set"]}
        return self.docs[query["cache_key"]]


def make_runtime():
    runtime = DBCacheRuntime()
    runtime.cache = FakeCollection()
    return runtime


def test_nested_dataframe_roundtrip():
    runtime = make_runtime()
    frame = pd.DataFrame(
        np.arange(6, dtype=np.float32).reshape(2, 3),
        index=["sample_a", "sample_b"],
        columns=["P1", "P2", "P3"],
    )
    block = {
        "submission_tag": "4N2Ti9Z3dC",
        "sample_tags": ["sample_a", "sample_b"],
        "proteins": ["P1", "P2", "P3"],
        "matrix": frame,
    }

    assert runtime.set("projection_block:test", block, cache_time=timedelta(hours=1))

    restored = runtime.get("projection_block:test")
    assert restored["submission_tag"] == "4N2Ti9Z3dC"
    assert restored["sample_tags"] == ["sample_a", "sample_b"]
    assert restored["proteins"] == ["P1", "P2", "P3"]
    pd.testing.assert_frame_equal(restored["matrix"], frame, check_dtype=False)


def test_nested_series_and_list_roundtrip():
    runtime = make_runtime()
    payload = {
        "series": pd.Series([1.0, 2.0], index=["a", "b"], name="zscores"),
        "blocks": [pd.DataFrame([[1.0]], index=["s"], columns=["P"]), "plain"],
    }

    assert runtime.set("nested:test", payload, cache_time=timedelta(hours=1))

    restored = runtime.get("nested:test")
    assert restored["blocks"][1] == "plain"
    assert restored["series"].name == "zscores"
    assert restored["blocks"][0].shape == (1, 1)


def test_stored_document_is_bson_encodable():
    runtime = make_runtime()
    frame = pd.DataFrame([[0.5]], index=["s"], columns=["P"])
    serialized = DBCacheRuntime._serialize({"matrix": frame, "tags": ("a", "b")})

    def assert_bson_native(value):
        if isinstance(value, dict):
            for v in value.values():
                assert_bson_native(v)
        elif isinstance(value, list):
            for v in value:
                assert_bson_native(v)
        else:
            assert isinstance(value, (str, int, float, bool, type(None)))

    assert_bson_native(serialized)

import json

import numpy as np
import pandas as pd
import pytest
from sklearn.decomposition import PCA

from services.statistics.projection import (
    assemble_pooled_pca,
    block_cache_key,
    build_submission_block,
    enrich_result_with_conditions,
    find_driver,
    get_sample_condition_map,
    protein_condition_association,
    resolve_visible_submission_tags,
    result_cache_key,
)


class FakeSubmissions:
    def __init__(self, matrices):
        self._matrices = matrices

    def get_zscore_matrix(self, tag):
        return self._matrices.get(tag)


class FakeDB:
    def __init__(self, matrices):
        self.submissions = FakeSubmissions(matrices)


def make_block(submission_tag, sample_tags, proteins, seed):
    rng = np.random.default_rng(seed)
    matrix = pd.DataFrame(
        rng.normal(size=(len(sample_tags), len(proteins))).astype(np.float32),
        index=sample_tags,
        columns=proteins,
    )
    return {
        "submission_tag": submission_tag,
        "sample_tags": sample_tags,
        "proteins": proteins,
        "matrix": matrix,
    }


def test_resolve_visible_submission_tags_scope_semantics():
    proteome_tags = ["sub_a", "sub_b", "sub_c"]
    assert resolve_visible_submission_tags(None, proteome_tags) == proteome_tags
    assert resolve_visible_submission_tags([], proteome_tags) == []
    assert resolve_visible_submission_tags(["sub_c", "sub_x"], proteome_tags) == ["sub_c"]


def test_build_submission_block_filters_sparse_proteins_and_imputes():
    matrix = pd.DataFrame(
        [
            [1.0, np.nan, 3.0],
            [2.0, np.nan, np.nan],
            [np.nan, 1.0, 1.0],
        ],
        index=["pg_keep", "pg_sparse", "pg_keep2"],
        columns=["s1", "s2", "s3"],
    )
    db = FakeDB({"sub_1": matrix})
    block = build_submission_block(db, "sub_1", min_valid_fraction=0.5)

    assert block is not None
    assert block["submission_tag"] == "sub_1"
    assert block["sample_tags"] == ["s1", "s2", "s3"]
    assert "pg_sparse" not in block["proteins"]
    assert set(block["proteins"]) == {"pg_keep", "pg_keep2"}
    assert block["matrix"].shape == (3, 2)
    assert not block["matrix"].isna().any().any()


def test_build_submission_block_returns_none_without_data():
    db = FakeDB({"sub_1": pd.DataFrame()})
    assert build_submission_block(db, "sub_1") is None
    assert build_submission_block(FakeDB({}), "missing") is None


def test_assemble_pooled_pca_matches_direct_pca_on_stacked_matrix():
    blocks = [
        make_block("sub_1", ["s1", "s2", "s3"], ["p1", "p2", "p3", "p4"], seed=1),
        make_block("sub_2", ["s4", "s5"], ["p2", "p3", "p4", "p5"], seed=2),
        make_block("sub_3", ["s6", "s7"], ["p1", "p2", "p3", "p5"], seed=3),
    ]
    result = assemble_pooled_pca(blocks, n_components=2, min_block_occurrence=2)

    universe = sorted({"p1", "p2", "p3", "p4", "p5"})
    expected_frames = [b["matrix"].reindex(columns=universe).fillna(0.0) for b in blocks]
    X = pd.concat(expected_frames, axis=0, ignore_index=True).to_numpy(dtype=np.float64)
    pca = PCA(n_components=2).fit(X)

    assert result["n_proteins"] == 5
    assert len(result["points"]) == 7
    np.testing.assert_allclose(result["variance_explained"], pca.explained_variance_ratio_)
    expected_scores = pca.transform(X)
    actual_scores = np.array([p["components"] for p in result["points"]])
    for col in range(2):
        assert np.allclose(np.abs(actual_scores[:, col]), np.abs(expected_scores[:, col]))
    assert [p["submission_tag"] for p in result["points"]] == ["sub_1"] * 3 + ["sub_2"] * 2 + ["sub_3"] * 2
    assert [p["sample_tag"] for p in result["points"]] == ["s1", "s2", "s3", "s4", "s5", "s6", "s7"]

    assert [d["tag"] for d in result["drivers"]] == universe
    expected_loadings = pca.components_.T
    actual_loadings = np.array([d["components"] for d in result["drivers"]])
    assert actual_loadings.shape == (5, 2)
    for col in range(2):
        assert np.allclose(np.abs(actual_loadings[:, col]), np.abs(expected_loadings[:, col]))


def test_assemble_pooled_pca_excludes_singleton_proteins():
    blocks = [
        make_block("sub_1", ["s1", "s2"], ["p_shared", "p_unique"], seed=4),
        make_block("sub_2", ["s3", "s4"], ["p_shared", "p_other"], seed=5),
    ]
    result = assemble_pooled_pca(blocks, n_components=1, min_block_occurrence=2)
    assert result["n_proteins"] == 1


def test_assemble_pooled_pca_raises_without_blocks():
    with pytest.raises(ValueError):
        assemble_pooled_pca([], n_components=2)


def test_result_cache_key_depends_on_visible_scope():
    key_a = result_cache_key("prot_1", ["sub_a", "sub_b"])
    key_b = result_cache_key("prot_1", ["sub_a"])
    key_c = result_cache_key("prot_1", ["sub_b", "sub_a"])
    key_other_proteome = result_cache_key("prot_2", ["sub_a", "sub_b"])

    assert key_a != key_b
    assert key_a == key_c  # order of the scope does not matter
    assert key_a != key_other_proteome
    assert key_a.startswith("proteome_projection:prot_1:")


def test_block_cache_key_is_namespaced_per_submission():
    assert block_cache_key("sub_a") != block_cache_key("sub_b")
    assert block_cache_key("sub_a").startswith("projection_block:")


def test_find_driver_returns_loadings_or_none():
    blocks = [
        make_block("sub_1", ["s1", "s2"], ["p1", "p2"], seed=8),
        make_block("sub_2", ["s3", "s4"], ["p1", "p2"], seed=9),
    ]
    result = assemble_pooled_pca(blocks, n_components=2)
    driver = find_driver(result, "p1")
    assert driver is not None
    assert driver["tag"] == "p1"
    assert len(driver["components"]) == 2
    assert find_driver(result, "p_missing") is None


class FakeSamples:
    def __init__(self, ca_by_submission):
        self._ca = ca_by_submission

    def get_condition_applications_by_sample_for_submission(self, submission_tag, sort_ca_tags=True, return_sample_index=False):
        return self._ca[submission_tag]


def test_get_sample_condition_map_keys_by_submission_and_sample():
    ca = pd.DataFrame({"att_disease": ["ca_a", "ca_b"], "att_treatment": [None, "ca_c"]}, index=["s1", "s2"])
    db = FakeDB({})
    db.samples = FakeSamples({"sub_1": ca})
    mapping = get_sample_condition_map(db, ["sub_1"])
    assert mapping[("sub_1", "s1")] == ["ca_a"]
    assert mapping[("sub_1", "s2")] == ["ca_b", "ca_c"]


def test_enrich_result_with_conditions_annotates_points_and_centroids():
    blocks = [
        make_block("sub_1", ["s1", "s2"], ["p1", "p2"], seed=10),
        make_block("sub_2", ["s3"], ["p1", "p2"], seed=11),
    ]
    result = assemble_pooled_pca(blocks, n_components=2)
    sample_ca_map = {("sub_1", "s1"): ["ca_a"], ("sub_1", "s2"): ["ca_a"], ("sub_2", "s3"): ["ca_b"]}
    enriched = enrich_result_with_conditions(result, sample_ca_map)

    by_sample = {p["sample_tag"]: p for p in enriched["points"]}
    assert by_sample["s1"]["condition_applications"] == ["ca_a"]
    assert by_sample["s3"]["condition_applications"] == ["ca_b"]

    centroids = {c["condition_application_tag"]: c for c in enriched["condition_centroids"]}
    assert centroids["ca_a"]["count"] == 2
    assert centroids["ca_b"]["count"] == 1
    expected_ca_a = (by_sample["s1"]["components"][0] + by_sample["s2"]["components"][0]) / 2
    assert centroids["ca_a"]["components"][0] == pytest.approx(expected_ca_a)
    # cached result is not mutated
    assert "condition_centroids" not in result
    assert "condition_applications" not in result["points"][0]
    json.dumps(enriched, allow_nan=False)


def test_protein_condition_association_ranks_conditions_by_mean_z():
    block = make_block("sub_1", ["s1", "s2", "s3"], ["p1"], seed=12)
    block["matrix"].loc["s1", "p1"] = 2.0
    block["matrix"].loc["s2", "p1"] = 1.0
    block["matrix"].loc["s3", "p1"] = -3.0
    sample_ca_map = {("sub_1", "s1"): ["ca_high"], ("sub_1", "s2"): ["ca_high"], ("sub_1", "s3"): ["ca_low"]}
    associations = protein_condition_association([block], sample_ca_map, "p1")
    assert [a["condition_application_tag"] for a in associations] == ["ca_high", "ca_low"]
    assert associations[0]["mean_z"] == pytest.approx(1.5)
    assert associations[0]["n_samples"] == 2
    assert associations[1]["mean_z"] == pytest.approx(-3.0)
    assert protein_condition_association([block], sample_ca_map, "p_missing") == []


def test_projection_points_are_json_safe():
    blocks = [
        make_block("sub_1", ["s1", "s2"], ["p1", "p2"], seed=6),
        make_block("sub_2", ["s3", "s4"], ["p1", "p2"], seed=7),
    ]
    result = assemble_pooled_pca(blocks, n_components=2)
    json.dumps(result, allow_nan=False)

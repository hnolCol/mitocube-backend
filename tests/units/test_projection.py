import json

import numpy as np
import pandas as pd
import pytest
from sklearn.decomposition import PCA

from services.statistics.projection import (
    assemble_pooled_pca,
    block_cache_key,
    build_submission_block,
    compute_ca_separation,
    compute_attribute_protein_effects,
    compute_condition_effects,
    compute_protein_ca_effects,
    compute_universe,
    enrich_result_with_conditions,
    find_driver,
    get_ca_attribute_map,
    get_sample_condition_map,
    protein_condition_association,
    rank_protein_attributes,
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


def test_compute_condition_effects_ranks_by_absolute_effect():
    block = make_block("sub_1", ["s1", "s2", "s3"], ["p1", "p2"], seed=13)
    block["matrix"].loc["s1", "p1"] = 2.0
    block["matrix"].loc["s2", "p1"] = 1.0
    block["matrix"].loc["s3", "p1"] = -3.0
    block["matrix"].loc["s1", "p2"] = -1.0
    block["matrix"].loc["s2", "p2"] = -1.0
    block["matrix"].loc["s3", "p2"] = 1.0
    sample_ca_map = {("sub_1", "s1"): ["ca_x"], ("sub_1", "s2"): ["ca_x"], ("sub_1", "s3"): []}

    result = compute_condition_effects([block], sample_ca_map, "ca_x")

    assert result["ca_tag"] == "ca_x"
    assert result["n_proteins"] == 2
    top = result["effects"][0]
    assert top["tag"] == "p1"
    assert top["effect"] == pytest.approx(4.5)
    assert top["mean_z_in"] == pytest.approx(1.5)
    assert top["mean_z_out"] == pytest.approx(-3.0)
    assert top["n_in"] == 2 and top["n_out"] == 1
    assert top["cohens_d"] == pytest.approx(9.0)
    assert result["effects"][1]["tag"] == "p2"
    assert result["effects"][1]["effect"] == pytest.approx(-2.0)
    json.dumps(result, allow_nan=False)


def test_compute_condition_effects_skips_proteins_missing_in_one_group():
    block_in = make_block("sub_1", ["s1"], ["p_shared", "p_only_in"], seed=14)
    block_out = make_block("sub_2", ["s2"], ["p_shared", "p_only_out"], seed=15)
    sample_ca_map = {("sub_1", "s1"): ["ca_x"], ("sub_2", "s2"): []}
    result = compute_condition_effects([block_in, block_out], sample_ca_map, "ca_x")
    tags = [e["tag"] for e in result["effects"]]
    assert tags == ["p_shared"]
    assert result["n_proteins"] == 1


def test_compute_universe_matches_assemble_filtering():
    blocks = [
        make_block("sub_1", ["s1", "s2"], ["p_shared", "p_unique"], seed=16),
        make_block("sub_2", ["s3", "s4"], ["p_shared", "p_other"], seed=17),
    ]
    assert compute_universe(blocks, min_block_occurrence=2) == ["p_shared"]


def test_get_ca_attribute_map_maps_ca_to_attribute():
    ca = pd.DataFrame({"att_compound": ["ca_a", "ca_b"], "att_disease": ["ca_c", "ca_c"]}, index=["s1", "s2"])
    db = FakeDB({})
    db.samples = FakeSamples({"sub_1": ca})
    mapping = get_ca_attribute_map(db, ["sub_1"])
    assert mapping == {"ca_a": "att_compound", "ca_b": "att_compound", "ca_c": "att_disease"}


def test_compute_ca_separation_weights_centroid_distance_by_variance():
    result = {
        "n_components": 2,
        "variance_explained": [0.6, 0.4],
        "points": [
            {"sample_tag": "s1", "submission_tag": "sub_1", "components": [2.0, 0.0]},
            {"sample_tag": "s2", "submission_tag": "sub_1", "components": [0.0, 1.0]},
            {"sample_tag": "s3", "submission_tag": "sub_1", "components": [-2.0, 0.0]},
        ],
    }
    sample_ca_map = {("sub_1", "s1"): ["ca_x"], ("sub_1", "s2"): ["ca_x"], ("sub_1", "s3"): []}
    # mean_in = [1, 0.5], mean_out = [-2, 0] -> diffs [3, 0.5] -> 0.6*9 + 0.4*0.25 = 5.5
    assert compute_ca_separation(result, sample_ca_map, "ca_x") == pytest.approx(5.5)
    assert compute_ca_separation(result, sample_ca_map, "ca_missing") == 0.0


def test_compute_protein_ca_effects_and_rank_attributes():
    block = make_block("sub_1", ["s1", "s2", "s3"], ["p1"], seed=18)
    block["matrix"].loc["s1", "p1"] = 3.0
    block["matrix"].loc["s2", "p1"] = 1.0
    block["matrix"].loc["s3", "p1"] = -2.0
    sample_ca_map = {
        ("sub_1", "s1"): ["ca_drug"],
        ("sub_1", "s2"): ["ca_drug", "ca_disease"],
        ("sub_1", "s3"): ["ca_disease"],
    }
    ca_attribute_map = {"ca_drug": "att_compound", "ca_disease": "att_disease"}

    effects = compute_protein_ca_effects([block], sample_ca_map, "p1")
    # ca_drug: in mean (3+1)/2=2, out mean -2 -> effect 4; ca_disease: in mean (1-2)/2=-0.5, out 3 -> effect -3.5
    assert effects["ca_drug"]["effect"] == pytest.approx(4.0)
    assert effects["ca_disease"]["effect"] == pytest.approx(-3.5)
    assert effects["ca_drug"]["n_in"] == 2 and effects["ca_drug"]["n_out"] == 1

    ranked = rank_protein_attributes(effects, ca_attribute_map)
    assert [r["attribute_tag"] for r in ranked] == ["att_compound", "att_disease"]
    assert ranked[0]["ca_tag"] == "ca_drug"
    assert ranked[0]["effect"] == pytest.approx(4.0)
    json.dumps(ranked, allow_nan=False)


def test_rank_protein_attributes_picks_best_ca_per_attribute():
    ca_effects = {
        "ca_a": {"effect": 1.0, "mean_z_in": 1.0, "mean_z_out": 0.0, "n_in": 2, "n_out": 2},
        "ca_b": {"effect": -5.0, "mean_z_in": -2.0, "mean_z_out": 3.0, "n_in": 2, "n_out": 2},
    }
    ca_attribute_map = {"ca_a": "att_x", "ca_b": "att_x"}
    ranked = rank_protein_attributes(ca_effects, ca_attribute_map)
    assert len(ranked) == 1
    assert ranked[0]["ca_tag"] == "ca_b"
    assert ranked[0]["effect"] == pytest.approx(-5.0)


def test_projection_points_are_json_safe():
    blocks = [
        make_block("sub_1", ["s1", "s2"], ["p1", "p2"], seed=6),
        make_block("sub_2", ["s3", "s4"], ["p1", "p2"], seed=7),
    ]
    result = assemble_pooled_pca(blocks, n_components=2)
    json.dumps(result, allow_nan=False)


def test_compute_attribute_protein_effects_ranks_and_reports_conditions():
    block_1 = make_block("sub_1", ["s1", "s2", "s3"], ["p1", "p2"], seed=20)
    block_1["matrix"]["p1"] = [3.0, 1.0, -2.0]
    block_1["matrix"]["p2"] = [0.5, 0.5, 0.5]
    block_2 = make_block("sub_2", ["s4", "s5"], ["p1", "p2"], seed=21)
    block_2["matrix"]["p1"] = [-1.0, 2.0]
    block_2["matrix"]["p2"] = [1.0, 1.0]
    blocks = [block_1, block_2]
    sample_ca_map = {
        ("sub_1", "s1"): ["ca_a"],
        ("sub_1", "s2"): ["ca_b"],
        ("sub_1", "s3"): [],
        ("sub_2", "s4"): ["ca_a"],
        ("sub_2", "s5"): ["ca_b"],
    }

    proteins = compute_attribute_protein_effects(blocks, sample_ca_map, ["ca_b", "ca_a"], limit=10)

    # attribute group: s1, s2, s4, s5 in; s3 out
    # p1: mean_in (3+1-1+2)/4 = 1.25, mean_out -2 -> effect 3.25
    # p2: mean_in (0.5+0.5+1+1)/4 = 0.75, mean_out 0.5 -> effect 0.25
    assert [p["tag"] for p in proteins] == ["p1", "p2"]
    assert proteins[0]["rank"] == 1 and proteins[1]["rank"] == 2
    assert proteins[0]["effect"] == pytest.approx(3.25)
    assert proteins[1]["effect"] == pytest.approx(0.25)

    conditions = {c["ca_tag"]: c for c in proteins[0]["conditions"]}
    # ca_a on p1: samples s1, s4 -> mean (3-1)/2 = 1, from 2 submissions
    assert conditions["ca_a"]["mean_z"] == pytest.approx(1.0)
    assert conditions["ca_a"]["n_samples"] == 2
    assert conditions["ca_a"]["n_submissions"] == 2
    # ca_b on p1: samples s2, s5 -> mean (1+2)/2 = 1.5
    assert conditions["ca_b"]["mean_z"] == pytest.approx(1.5)
    assert conditions["ca_b"]["n_samples"] == 2
    assert [c["ca_tag"] for c in proteins[0]["conditions"]] == ["ca_a", "ca_b"]
    json.dumps(proteins, allow_nan=False)


def test_compute_attribute_protein_effects_respects_limit_and_missing_proteins():
    block = make_block("sub_1", ["s1", "s2"], ["p1", "p2", "p3"], seed=22)
    block["matrix"]["p1"] = [5.0, -5.0]
    block["matrix"]["p2"] = [1.0, -1.0]
    block["matrix"]["p3"] = [0.0, 0.0]
    sample_ca_map = {("sub_1", "s1"): ["ca_a"], ("sub_1", "s2"): []}

    proteins = compute_attribute_protein_effects([block], sample_ca_map, ["ca_a"], limit=1)
    assert len(proteins) == 1
    assert proteins[0]["tag"] == "p1"
    assert proteins[0]["effect"] == pytest.approx(10.0)
    assert proteins[0]["conditions"][0]["n_submissions"] == 1

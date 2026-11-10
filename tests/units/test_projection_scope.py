"""Scope-isolation tests for the proteome projection endpoints.

Drives the real router functions with a fake database and a cache bypass to
prove that every response is built exclusively from submissions inside the
requesting user's scope, for all role cases (curator, standard, guest).
"""
import numpy as np
import pandas as pd
import pytest
from fastapi import HTTPException

from config.models.user import UserModel
from routers.stats import projection as projection_router
from services.statistics import projection as projection_service


PROTEOME = "prot_1"
ALL_SUBMISSIONS = ["sub_a", "sub_b", "sub_c", "sub_d"]


def make_matrix(seed):
    rng = np.random.default_rng(seed)
    return pd.DataFrame(
        rng.normal(size=(4, 4)),
        index=[f"pg_{i}" for i in range(4)],
        columns=[f"s{i}" for i in range(4)],
    )


class FakeProteomes:
    def exists(self, tag):
        return tag == PROTEOME


class FakeSubmissions:
    def __init__(self):
        self.requested_matrices = []

    def get_tags_by_proteome(self, proteome_tag):
        assert proteome_tag == PROTEOME
        return list(ALL_SUBMISSIONS)

    def get_zscore_matrix(self, tag, annotation_tag=None):
        self.requested_matrices.append(tag)
        return make_matrix(seed=abs(hash(tag)) % 1000)


class FakeSubmissionFilter:
    def __init__(self, scopes):
        self._scopes = scopes

    def get_user_submission_scope_tags(self, user_tag):
        return self._scopes[user_tag]


class FakeSamples:
    def get_condition_applications_by_sample_for_submission(self, submission_tag, sort_ca_tags=True, return_sample_index=False):
        return pd.DataFrame({"att_disease": ["ca_x"] * 4}, index=[f"s{i}" for i in range(4)])


class FakeDB:
    def __init__(self, scopes):
        self.proteomes = FakeProteomes()
        self.submissions = FakeSubmissions()
        self.submission_filter = FakeSubmissionFilter(scopes)
        self.samples = FakeSamples()


def utag(tag):
    return (tag + "0000000")[:8]


def make_user(tag):
    return UserModel(tag=utag(tag), firstname="Test", lastname="User",
                     email=f"{tag}@uni-koeln.de", created_at=0.0)


@pytest.fixture(autouse=True)
def bypass_cache(monkeypatch):
    """Bypass the Mongo-backed runtime cache: always compute, but record keys."""
    keys = []

    def fake_get_or_compute(cache_key, compute_fn, cache_time, **kwargs):
        keys.append(cache_key)
        return compute_fn()

    monkeypatch.setattr(projection_service.db_cache_runtime, "get_or_compute", fake_get_or_compute)
    monkeypatch.setattr(projection_router.db_cache_runtime, "get_or_compute", fake_get_or_compute)
    return keys


def test_curator_sees_all_proteome_submissions(bypass_cache):
    db = FakeDB({utag("curator"): None})
    response = projection_router.get_proteome_projection(
        proteome_tag=PROTEOME, method="pca", n_components=2,
        min_valid_fraction=0.5, user=make_user("curator"), db=db)
    assert response.submission_tags == sorted(ALL_SUBMISSIONS)
    assert {p.submission_tag for p in response.points} == set(ALL_SUBMISSIONS)
    assert sorted(db.submissions.requested_matrices) == sorted(ALL_SUBMISSIONS)


def test_standard_user_sees_only_intersection(bypass_cache):
    db = FakeDB({utag("alice"): ["sub_a", "sub_b", "sub_unrelated"]})
    response = projection_router.get_proteome_projection(
        proteome_tag=PROTEOME, method="pca", n_components=2,
        min_valid_fraction=0.5, user=make_user("alice"), db=db)
    assert response.submission_tags == ["sub_a", "sub_b"]
    assert {p.submission_tag for p in response.points} == {"sub_a", "sub_b"}
    assert sorted(db.submissions.requested_matrices) == ["sub_a", "sub_b"]
    assert "sub_c" not in db.submissions.requested_matrices


def test_guest_gets_404_and_no_data_access(bypass_cache):
    db = FakeDB({utag("guest"): []})
    with pytest.raises(HTTPException) as exc_info:
        projection_router.get_proteome_projection(
            proteome_tag=PROTEOME, method="pca", n_components=2,
            min_valid_fraction=0.5, user=make_user("guest"), db=db)
    assert exc_info.value.status_code == 404
    assert db.submissions.requested_matrices == []


def test_unknown_proteome_is_404_for_every_role(bypass_cache):
    db = FakeDB({utag("curator"): None})
    with pytest.raises(HTTPException) as exc_info:
        projection_router.get_proteome_projection(
            proteome_tag="prot_missing", method="pca", n_components=2,
            min_valid_fraction=0.5, user=make_user("curator"), db=db)
    assert exc_info.value.status_code == 404


def test_different_scopes_produce_different_cache_keys_and_disjoint_results(bypass_cache):
    db = FakeDB({utag("alice"): ["sub_a", "sub_b"], utag("bob"): ["sub_c", "sub_d"]})
    keys = bypass_cache
    resp_a = projection_router.get_proteome_projection(
        proteome_tag=PROTEOME, method="pca", n_components=2,
        min_valid_fraction=0.5, user=make_user("alice"), db=db)
    resp_b = projection_router.get_proteome_projection(
        proteome_tag=PROTEOME, method="pca", n_components=2,
        min_valid_fraction=0.5, user=make_user("bob"), db=db)
    assert resp_a.submission_tags == ["sub_a", "sub_b"]
    assert resp_b.submission_tags == ["sub_c", "sub_d"]
    result_keys = [k for k in keys if k.startswith(f"{projection_service.PROJECTION_RESULT_NAMESPACE}:{PROTEOME}:")]
    assert len(result_keys) == 2
    assert result_keys[0] != result_keys[1]


def test_effects_endpoint_respects_scope(bypass_cache):
    db = FakeDB({utag("alice"): ["sub_a"]})
    response = projection_router.get_proteome_projection_condition_effects(
        proteome_tag=PROTEOME, ca_tag="ca_x", limit=10,
        min_valid_fraction=0.5, user=make_user("alice"), db=db)
    assert response.submission_tags == ["sub_a"]
    assert all(e.n_in + e.n_out == 4 for e in response.effects)


def test_effects_endpoint_404_for_ca_outside_scope(bypass_cache):
    db = FakeDB({utag("alice"): ["sub_a"]})
    # samples of sub_a only carry ca_x; ca_y must not be found
    with pytest.raises(HTTPException) as exc_info:
        projection_router.get_proteome_projection_condition_effects(
            proteome_tag=PROTEOME, ca_tag="ca_y", limit=10,
            min_valid_fraction=0.5, user=make_user("alice"), db=db)
    assert exc_info.value.status_code == 404

"""Unit tests for the 1D shift analysis (systematic shifted annotations).

Covers the pure statistics helper (Mann-Whitney U per annotation, member
values vs. all other values) and the POST /api/annotations/analysis/shift
router endpoint driven with a fake database for both universe scopes.
"""
import numpy as np
import pandas as pd
import pytest
from fastapi import HTTPException
from scipy.stats import mannwhitneyu

from config.models.annotations.annotations import AnnotationShiftRequestModel
from config.models.user import UserModel
from routers.annotations import annotations as annotations_router
from services.annotations.enrichment import compute_annotation_shift, compute_annotation_shift_from_member_values, enrichment_records


@pytest.fixture(autouse=True)
def bypass_cache(monkeypatch):
    """Bypass the Mongo-backed runtime cache so every test computes fresh."""
    def fake_get_or_compute(cache_key, compute_fn, cache_time, **kwargs):
        return compute_fn()
    monkeypatch.setattr(annotations_router.db_cache_runtime, "get_or_compute", fake_get_or_compute)


def make_user(tag="testuser"):
    return UserModel(tag=tag, firstname="Test", lastname="User",
                     email=f"{tag}@uni-koeln.de", created_at=0.0)


# ---------------------------------------------------------------------------
# pure statistics helper
# ---------------------------------------------------------------------------

def test_compute_shift_matches_mannwhitneyu():
    rng = np.random.default_rng(0)
    universe = [f"p{i}" for i in range(100)]
    members = universe[:20]
    values = {p: float(rng.normal(0, 1)) for p in universe[20:]}
    values.update({p: float(rng.normal(2.0, 1)) for p in members})  # shifted up
    members_df = pd.DataFrame({
        "annotation_tag": ["ann_up"],
        "text": ["Up term"],
        "protein_tags": [members],
    })
    result = compute_annotation_shift(values, members_df, min_size=3)
    assert len(result) == 1
    row = result.iloc[0]
    assert row["annotation_tag"] == "ann_up"
    assert row["n_in"] == 20
    assert row["n_out"] == 80
    assert row["direction"] == "up"
    assert row["shift"] == pytest.approx(row["mean_in"] - row["mean_out"])
    assert row["mean_in"] > row["mean_out"]
    expected_u, expected_p = mannwhitneyu([values[p] for p in members],
                                          [values[p] for p in universe[20:]],
                                          alternative="two-sided")
    assert row["u_statistic"] == pytest.approx(expected_u)
    assert row["p_value"] == pytest.approx(expected_p)
    assert row["p_value"] < 0.001  # clearly shifted
    assert row["fdr"] == pytest.approx(row["p_value"])  # single test: fdr == p


def test_compute_shift_direction_down_and_min_size():
    values = {f"p{i}": (0.0 if i < 10 else 1.0) for i in range(50)}
    members_df = pd.DataFrame({
        "annotation_tag": ["ann_down", "ann_small"],
        "text": ["Down", "Small"],
        "protein_tags": [[f"p{i}" for i in range(10)], ["p0", "p1"]],
    })
    result = compute_annotation_shift(values, members_df, min_size=3)
    assert list(result["annotation_tag"]) == ["ann_down"]  # ann_small filtered by min_size
    assert result.iloc[0]["direction"] == "down"
    assert result.iloc[0]["shift"] < 0


def test_compute_shift_empty_and_too_few_values():
    members_df = pd.DataFrame({
        "annotation_tag": ["a"], "text": ["A"], "protein_tags": [["p0", "p1", "p2"]],
    })
    assert compute_annotation_shift({}, members_df).empty
    assert compute_annotation_shift({"p0": 1.0, "p1": 2.0}, members_df, min_size=3).empty
    assert compute_annotation_shift({f"p{i}": 1.0 for i in range(10)},
                                    pd.DataFrame(columns=["annotation_tag", "text", "protein_tags"])).empty


def test_shift_records_json_safe():
    values = {f"p{i}": float(i) for i in range(30)}
    members_df = pd.DataFrame({
        "annotation_tag": ["ann_x"], "text": ["X"],
        "protein_tags": [[f"p{i}" for i in range(10)]],
    })
    result = compute_annotation_shift(values, members_df)
    records = enrichment_records(result, limit=10)
    assert len(records) == 1
    assert all(not (isinstance(v, float) and np.isnan(v)) for r in records for v in r.values())


# ---------------------------------------------------------------------------
# router endpoint with a fake database
# ---------------------------------------------------------------------------

class FakeSubmissions:
    def __init__(self, proteins_by_tag):
        self._proteins_by_tag = proteins_by_tag

    def get_proteins_in_submission(self, tag):
        return self._proteins_by_tag[tag]


class FakeProteins:
    def __init__(self, proteins_by_proteome):
        self._proteins_by_proteome = proteins_by_proteome

    def get_protein_tags_by_proteome(self, proteome_tag):
        return self._proteins_by_proteome[proteome_tag]


class FakeAnnotations:
    def __init__(self, member_values):
        self._member_values = member_values
        self.calls = []

    def get_annotation_member_values(self, universe_proteins, protein_values, min_size=3, group_tag=None):
        self.calls.append({"universe": list(universe_proteins), "min_size": min_size, "group_tag": group_tag})
        return self._member_values


class FakeDB:
    def __init__(self, submissions, proteins, annotations):
        self.submissions = submissions
        self.proteins = proteins
        self.annotations = annotations


def make_fake_db():
    universe = [f"p{i}" for i in range(50)]
    # member values matching the test values below (members p0..p9 have value 2.0)
    member_values = pd.DataFrame({
        "annotation_tag": ["ann_up", "ann_flat"],
        "text": ["Up term", "Flat term"],
        "member_values": [[2.0] * 10, [0.0] * 10],
    })
    return FakeDB(
        submissions=FakeSubmissions({"sub_a": universe}),
        proteins=FakeProteins({"prot_1": universe}),
        annotations=FakeAnnotations(member_values),
    )


def make_request(values, **kwargs):
    return AnnotationShiftRequestModel(protein_values=values, **kwargs)


def test_router_shift_submission_scope(monkeypatch):
    db = make_fake_db()
    checked = []
    monkeypatch.setattr(annotations_router, "check_submission_tags_access",
                        lambda submission_tags, user, db=None: checked.append(list(submission_tags)) or True)
    universe = [f"p{i}" for i in range(50)]
    values = {p: (2.0 if i < 10 else 0.0) for i, p in enumerate(universe)}
    result = annotations_router.annotation_shift_analysis(
        request=make_request(values, submission_tags=["sub_a"], min_size=3, limit=None),
        user=make_user(), db=db)
    assert checked == [["sub_a"]]
    assert db.annotations.calls[0]["universe"] == sorted(universe)
    assert result[0]["annotation_tag"] == "ann_up"
    assert result[0]["direction"] == "up"
    assert result[0]["n_in"] == 10
    assert result[0]["n_out"] == 40
    assert result[0]["p_value"] < result[1]["p_value"]


def test_router_shift_proteome_scope_and_value_filtering(monkeypatch):
    db = make_fake_db()
    monkeypatch.setattr(annotations_router, "check_submission_tags_access",
                        lambda **kwargs: pytest.fail("access check must not be called for proteome scope"))
    universe = [f"p{i}" for i in range(50)]
    values = {p: (2.0 if i < 10 else 0.0) for i, p in enumerate(universe)}
    values["outside_proteome"] = 99.0  # not in universe -> ignored
    values["p49"] = float("nan")  # non-finite -> ignored
    result = annotations_router.annotation_shift_analysis(
        request=make_request(values, proteome_tag="prot_1", min_size=3, limit=None),
        user=make_user(), db=db)
    assert result[0]["n_out"] == 39  # p49 has no finite value
    assert all(r["annotation_tag"] != "outside_proteome" for r in result)


def test_router_shift_requires_exactly_one_universe_scope():
    db = make_fake_db()
    values = {f"p{i}": 1.0 for i in range(10)}
    with pytest.raises(HTTPException) as err:
        annotations_router.annotation_shift_analysis(
            request=make_request(values), user=make_user(), db=db)
    assert err.value.status_code == 400
    with pytest.raises(HTTPException) as err:
        annotations_router.annotation_shift_analysis(
            request=make_request(values, submission_tags=["sub_a"], proteome_tag="prot_1"),
            user=make_user(), db=db)
    assert err.value.status_code == 400


def test_router_shift_no_values_in_universe():
    db = make_fake_db()
    with pytest.raises(HTTPException) as err:
        annotations_router.annotation_shift_analysis(
            request=make_request({"unknown": 1.0}, proteome_tag="prot_1"),
            user=make_user(), db=db)
    assert err.value.status_code == 400

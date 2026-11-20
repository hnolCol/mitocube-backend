"""Unit tests for the annotation enrichment analysis.

Covers the pure statistics helper (services.annotations.enrichment) and the
/api/annotations/analysis/enrichment router endpoint driven with a fake
database, for both universe scopes: submission tags (submission-wide volcano
plots) and proteome tag (cross-submission comparisons of the same proteome).
"""
import numpy as np
import pandas as pd
import pytest
from fastapi import HTTPException
from scipy.stats import fisher_exact

from config.models.user import UserModel
from routers.annotations import annotations as annotations_router
from services.annotations.enrichment import compute_annotation_enrichment, enrichment_records


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

def test_compute_enrichment_matches_fisher_exact():
    overlap = pd.DataFrame({
        "annotation_tag": ["ann_enriched", "ann_neutral"],
        "text": ["Enriched term", "Neutral term"],
        "universe_count": [20, 50],
        "target_count": [8, 5],
    })
    target_size, universe_size = 10, 100
    result = compute_annotation_enrichment(overlap, target_size, universe_size)

    assert list(result.columns) == [
        "annotation_tag", "text", "target_with_annotation", "target_total",
        "universe_with_annotation", "universe_total", "odds_ratio", "p_value", "fdr",
    ]
    assert len(result) == 2
    # sorted by p-value: the enriched annotation comes first
    assert result.iloc[0]["annotation_tag"] == "ann_enriched"

    a, b = 8, target_size - 8
    c, d = 20 - 8, universe_size - target_size - 20 + 8
    _, expected_p = fisher_exact([[a, b], [c, d]], alternative="greater")
    assert result.iloc[0]["p_value"] == pytest.approx(expected_p)
    assert result.iloc[0]["target_with_annotation"] == 8
    assert result.iloc[0]["universe_with_annotation"] == 20
    assert result.iloc[0]["target_total"] == target_size
    assert result.iloc[0]["universe_total"] == universe_size


def test_compute_enrichment_fdr_is_bh():
    overlap = pd.DataFrame({
        "annotation_tag": [f"ann_{i}" for i in range(5)],
        "text": [f"term {i}" for i in range(5)],
        "universe_count": [10, 20, 30, 40, 50],
        "target_count": [9, 1, 2, 1, 0 + 1],
    })
    result = compute_annotation_enrichment(overlap, target_size=10, universe_size=100)
    p = result["p_value"].to_numpy()
    fdr = result["fdr"].to_numpy()
    # BH: fdr_i = p_i * m / rank_i (monotonicity enforced)
    m = len(p)
    order = np.argsort(p)
    ranks = np.empty(m, dtype=float)
    ranks[order] = np.arange(1, m + 1)
    expected = np.minimum.accumulate((p * m / ranks)[::-1])[::-1]
    assert np.allclose(np.sort(fdr), np.sort(expected))
    assert np.all(fdr >= p - 1e-12)


def test_compute_enrichment_min_overlap_filters():
    overlap = pd.DataFrame({
        "annotation_tag": ["ann_a", "ann_b"],
        "text": ["A", "B"],
        "universe_count": [5, 30],
        "target_count": [1, 4],
    })
    result = compute_annotation_enrichment(overlap, target_size=10, universe_size=100, min_overlap=2)
    assert list(result["annotation_tag"]) == ["ann_b"]


def test_compute_enrichment_empty_and_invalid():
    assert compute_annotation_enrichment(pd.DataFrame(columns=["annotation_tag", "text", "universe_count", "target_count"]), 10, 100).empty
    overlap = pd.DataFrame({"annotation_tag": ["a"], "text": ["A"], "universe_count": [5], "target_count": [3]})
    assert compute_annotation_enrichment(overlap, 0, 100).empty
    assert compute_annotation_enrichment(overlap, 10, 0).empty


def test_enrichment_records_are_json_safe_and_limited():
    overlap = pd.DataFrame({
        "annotation_tag": ["ann_a", "ann_b"],
        "text": ["A", "B"],
        "universe_count": [5, 30],
        "target_count": [3, 4],
    })
    result = compute_annotation_enrichment(overlap, target_size=10, universe_size=100)
    records = enrichment_records(result, limit=1)
    assert len(records) == 1
    assert all(not (isinstance(v, float) and np.isnan(v)) for r in records for v in r.values())
    # inf odds ratio (zero cell) becomes None
    overlap_zero = pd.DataFrame({
        "annotation_tag": ["ann_z"], "text": ["Z"], "universe_count": [4], "target_count": [4],
    })
    rec = enrichment_records(compute_annotation_enrichment(overlap_zero, 4, 100))[0]
    assert rec["odds_ratio"] is None or np.isfinite(rec["odds_ratio"])


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
    def __init__(self, overlap):
        self._overlap = overlap
        self.calls = []

    def get_annotation_overlap_counts(self, universe_proteins, target_proteins, group_tag=None, min_target_count=0):
        self.calls.append({"universe": list(universe_proteins), "target": list(target_proteins), "group_tag": group_tag})
        return self._overlap


class FakeDB:
    def __init__(self, submissions, proteins, annotations):
        self.submissions = submissions
        self.proteins = proteins
        self.annotations = annotations


def make_fake_db():
    universe_sub = [f"p{i}" for i in range(100)]
    overlap = pd.DataFrame({
        "annotation_tag": ["ann_hit", "ann_miss"],
        "text": ["Hit term", "Miss term"],
        "universe_count": [10, 40],
        "target_count": [8, 1],
    })
    db = FakeDB(
        submissions=FakeSubmissions({"sub_a": universe_sub[:60], "sub_b": universe_sub[40:]}),
        proteins=FakeProteins({"prot_1": universe_sub}),
        annotations=FakeAnnotations(overlap),
    )
    return db


def test_router_submission_universe(monkeypatch):
    db = make_fake_db()
    checked = []
    monkeypatch.setattr(annotations_router, "check_submission_tags_access",
                        lambda submission_tags, user, db=None: checked.append(list(submission_tags)) or True)
    user = make_user()
    target = ";".join([f"p{i}" for i in range(10)])
    result = annotations_router.annotation_enrichment_analysis(
        target_proteins=target, submission_tags="sub_a;sub_b", proteome_tag=None,
        group_tag=None, search_string=None, min_overlap=1, limit=None, user=user, db=db)
    assert checked == [["sub_a", "sub_b"]]
    # universe is the union of both submissions = all 100 proteins
    call = db.annotations.calls[0]
    assert len(call["universe"]) == 100
    assert call["target"] == [f"p{i}" for i in range(10)]
    assert result[0]["annotation_tag"] == "ann_hit"
    assert result[0]["p_value"] < result[1]["p_value"]
    assert result[0]["universe_total"] == 100
    assert result[0]["target_total"] == 10


def test_router_proteome_universe(monkeypatch):
    db = make_fake_db()
    monkeypatch.setattr(annotations_router, "check_submission_tags_access",
                        lambda **kwargs: pytest.fail("access check must not be called for proteome scope"))
    user = make_user()
    target = ";".join([f"p{i}" for i in range(10)])
    result = annotations_router.annotation_enrichment_analysis(
        target_proteins=target, submission_tags=None, proteome_tag="prot_1",
        group_tag=None, search_string=None, min_overlap=1, limit=None, user=user, db=db)
    assert db.annotations.calls[0]["universe"] == [f"p{i}" for i in range(100)]
    assert result[0]["universe_total"] == 100
    assert result[0]["target_total"] == 10


def test_router_requires_exactly_one_universe_scope():
    db = make_fake_db()
    user = make_user()
    target = "p0;p1"
    with pytest.raises(HTTPException) as err:
        annotations_router.annotation_enrichment_analysis(
            target_proteins=target, submission_tags=None, proteome_tag=None,
            group_tag=None, search_string=None, min_overlap=1, limit=None, user=user, db=db)
    assert err.value.status_code == 400
    with pytest.raises(HTTPException) as err:
        annotations_router.annotation_enrichment_analysis(
            target_proteins=target, submission_tags="sub_a", proteome_tag="prot_1",
            group_tag=None, search_string=None, min_overlap=1, limit=None, user=user, db=db)
    assert err.value.status_code == 400


def test_router_target_must_intersect_universe():
    db = make_fake_db()
    user = make_user()
    with pytest.raises(HTTPException) as err:
        annotations_router.annotation_enrichment_analysis(
            target_proteins="unknown1;unknown2", submission_tags=None, proteome_tag="prot_1",
            group_tag=None, search_string=None, min_overlap=1, limit=None, user=user, db=db)
    assert err.value.status_code == 400


def test_router_search_string_and_group_tag_and_limit(monkeypatch):
    db = make_fake_db()
    monkeypatch.setattr(annotations_router, "check_submission_tags_access", lambda **kwargs: True)
    user = make_user()
    target = ";".join([f"p{i}" for i in range(10)])
    result = annotations_router.annotation_enrichment_analysis(
        target_proteins=target, submission_tags="sub_a", proteome_tag=None,
        group_tag="group_1", search_string="hit", min_overlap=1, limit=5, user=user, db=db)
    assert db.annotations.calls[0]["group_tag"] == "group_1"
    assert all("hit" in r["text"].lower() for r in result)
    assert len(result) <= 5

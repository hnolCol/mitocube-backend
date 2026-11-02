"""
Route-level tests for the feature data endpoint, verifying the batched
data access (no per-sample DB round trips) and lost/excluded skipping.
"""

import sys
import time
from pathlib import Path

import pytest

SRC_DIR = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(SRC_DIR))

from config.enums.users.roles import UserRolesEnum
from config.models.user import UserModel
from services.users import get_user_from_token
from lib.database.Database import get_db


class FakeSamplesDB:
    def __init__(self):
        self.quant_calls = 0
        self.quant_values = {"sub-1|s1": 1.5, "sub-1|s2": 2.5}
        self.ca_map = None

    def get_quantified_data_for_features(self, tags, feature_tag, metrics="raw"):
        self.quant_calls += 1
        return {tag: self.quant_values[tag] for tag in tags if tag in self.quant_values}

    def get_condition_applications_by_sample_for_submission(self, submission_tag, **kwargs):
        import pandas as pd

        self.ca_map = pd.DataFrame(
            {"att_environment": ["env_a", "env_b"]},
            index=["sub-1|s1", "sub-1|s2"],
        )
        return self.ca_map

    def get_genotypes_by_sample_for_submission(self, submission_tag, **kwargs):
        import pandas as pd

        return pd.DataFrame({"att_genotype": ["wt", "ko"]}, index=["sub-1|s1", "sub-1|s2"])


class FakeSubmissionsDB:
    def get_samples(self, tag, ignore_excluded=False, ignore_lost=False):
        return ["sub-1|s1", "sub-1|s2", "sub-1|s3"]

    def has_genotypes(self, tag):
        return True


class FakeFeaturesDB:
    def exists(self, tag):
        return True


class FakeSubmissionFilterDB:
    def has_user_access(self, user_tag, submission_tag):
        return True


class FakeSubmissionsDBWithExists(FakeSubmissionsDB):
    def exists(self, tag):
        return True


class FakeDB:
    def __init__(self):
        self.samples = FakeSamplesDB()
        self.submissions = FakeSubmissionsDBWithExists()
        self.features = FakeFeaturesDB()
        self.submission_filter = FakeSubmissionFilterDB()


def make_user(role=UserRolesEnum.STANDARD):
    return UserModel(
        tag="abcdefgh",
        firstname="Test",
        lastname="User",
        email="test.user@age.mpg.de",
        created_at=time.time(),
        role=role,
        allow_login=True,
    )


@pytest.fixture
def db():
    return FakeDB()


@pytest.fixture
def client(db):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from routers.features.features import router as features_router

    app = FastAPI()
    app.include_router(features_router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_user_from_token] = lambda: make_user()
    with TestClient(app) as c:
        yield c


def test_feature_data_uses_batched_quantification(client, db):
    resp = client.get("/api/features/pg-1/d?submission_tag=sub-1")
    assert resp.status_code == 200
    body = resp.json()
    assert db.samples.quant_calls == 1
    values = {row["tag"]: row["value"] for row in body["data"]}
    assert values["sub-1|s1"] == 1.5
    assert values["sub-1|s2"] == 2.5
    assert values["sub-1|s3"] is None
    assert "att_environment" in body["attribute_tags"]
    assert "att_genotype" in body["attribute_tags"]


def test_feature_data_without_condition_procedures(client, db):
    resp = client.get("/api/features/pg-1/d?submission_tag=sub-1&append_condition_procedure=false")
    assert resp.status_code == 200
    body = resp.json()
    assert body["attribute_tags"] == []
    assert db.samples.quant_calls == 1

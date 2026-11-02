"""
Route-level tests for the per-sample quantification distribution endpoint,
verifying that excluded and lost samples are skipped.
"""

import sys
import time
from pathlib import Path

import pytest

SRC_DIR = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(SRC_DIR))

from config.enums.users.roles import UserRolesEnum
from config.models.user import UserModel
from config.models.calculations.quantile import QuantileModel
from services.users import get_user_from_token
from lib.database.Database import get_db


class FakeSamplesDB:
    def __init__(self):
        self.batch_calls = 0
        self.distributions = {
            "sub-1|s1": QuantileModel(tag="sub-1|s1", min=1.0, q25=2.0, m=3.0, q75=4.0, max=5.0, N=10),
            "sub-1|s2": QuantileModel(tag="sub-1|s2", min=1.0, q25=2.0, m=3.0, q75=4.0, max=5.0, N=10),
        }

    def get_condition_applications_by_sample_for_submission(self, submission_tag, return_sample_index=False, **kwargs):
        import pandas as pd

        return pd.DataFrame(
            {"att_environment": ["env_a", "env_b"]},
            index=["sub-1|s1", "sub-1|s2"],
        )

    def get_quantification_distribution(self, tag, quantification_type, annotation_tag=None):
        return self.distributions[tag]

    def get_quantification_distributions(self, tags, quantification_type, annotation_tag=None, remove_outlier=True):
        self.batch_calls += 1
        return {tag: self.distributions[tag] for tag in tags if tag in self.distributions}


class FakeSubmissionsDB:
    def __init__(self):
        self.get_samples_calls = []

    def exists(self, tag):
        return tag == "sub-1"

    def get_samples(self, tag, ignore_excluded=False, ignore_lost=False):
        self.get_samples_calls.append((tag, ignore_excluded, ignore_lost))
        if ignore_excluded or ignore_lost:
            return ["sub-1|s1", "sub-1|s2"]
        return ["sub-1|s1", "sub-1|s2", "sub-1|s3", "sub-1|s4"]

    def quantification_exists(self, tag, type):
        return True


class FakeSubmissionFilterDB:
    def has_user_access(self, user_tag, submission_tag):
        return True


class FakeDB:
    def __init__(self):
        self.samples = FakeSamplesDB()
        self.submissions = FakeSubmissionsDB()
        self.submission_filter = FakeSubmissionFilterDB()

    def get_datatable(self, *args, **kwargs):
        import pandas as pd

        return pd.DataFrame()


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
    from routers.submission.quantifications import router as quantifications_router

    app = FastAPI()
    app.include_router(quantifications_router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_user_from_token] = lambda: make_user()
    with TestClient(app) as c:
        yield c


def test_sample_quantification_distribution_skips_excluded_and_lost(client, db):
    resp = client.get("/api/submissions/sub-1/samples/quantifications/distribution?quantification_type=protein_groups")
    assert resp.status_code == 200
    body = resp.json()
    returned_tags = [entry[0] for entry in body]
    assert returned_tags == ["sub-1|s1", "sub-1|s2"]
    assert db.submissions.get_samples_calls[-1] == ("sub-1", True, True)


def test_sample_quantification_distribution_uses_batch_method(client, db):
    resp = client.get("/api/submissions/sub-1/samples/quantifications/distribution?quantification_type=protein_groups")
    assert resp.status_code == 200
    assert db.samples.batch_calls == 1

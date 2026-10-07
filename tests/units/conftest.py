import sys
from pathlib import Path
import pytest
from datetime import timedelta

SRC_DIR = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(SRC_DIR))

TEST_JWT_KEY = "test-jwt-key-not-for-production"
TEST_SHARE_KEY = "test-share-key-not-for-production"


class TestUserToken:
    expires_after_hours = timedelta(hours=1)
    expires_after_minutes = timedelta(minutes=15)
    jwt_key = type("S", (), {"get_secret_value": lambda self: TEST_JWT_KEY})()
    jwt_algorithm = "HS256"


class TestShareToken:
    expires_after_hours = timedelta(days=1)
    jwt_share_key = type("S", (), {"get_secret_value": lambda self: TEST_SHARE_KEY})()
    share_token_pw = type("S", (), {"get_secret_value": lambda self: "test-share-pw"})()
    jwt_algorithm = "HS256"


@pytest.fixture
def token_settings(monkeypatch):
    """Point the cached token settings used by services.encryption at test values.

    services.encryption resolves the settings once at import time, so the
    module-level objects must be replaced, not just the getters.
    """
    import services.encryption as encryption

    monkeypatch.setattr(encryption, "user_token_settings", TestUserToken())
    monkeypatch.setattr(encryption, "SHARE_TOKEN_SETTINGS", TestShareToken())
    return TestUserToken

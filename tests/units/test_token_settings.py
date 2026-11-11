import sys
from datetime import timedelta
from pathlib import Path

import pytest

SRC_DIR = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(SRC_DIR))

from config.settings.token import ShareToken  # noqa: E402

REQUIRED_SECRETS = {
    "JWT_SHARE_KEY": "test-share-key-not-for-production",
    "SHARE_TOKEN_PW": "test-share-pw",
}


@pytest.mark.parametrize("env_name", ["SHARE_EXPIRES_AFTER_HOURS", "share_expires_after_hours"])
def test_share_expires_after_hours_alias_is_case_insensitive(monkeypatch, env_name):
    monkeypatch.setenv(env_name, "5")
    for key, value in REQUIRED_SECRETS.items():
        monkeypatch.setenv(key, value)

    settings = ShareToken(_env_file=None)

    assert settings.expires_after_hours == timedelta(hours=5)


def test_share_expires_after_hours_default(monkeypatch):
    for key, value in REQUIRED_SECRETS.items():
        monkeypatch.setenv(key, value)

    settings = ShareToken(_env_file=None)

    assert settings.expires_after_hours == timedelta(days=120)

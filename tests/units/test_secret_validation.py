import os
import sys
from pathlib import Path

import pytest

SRC_DIR = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(SRC_DIR))

from config.secrets import validation  # noqa: E402

REQUIRED = {
    "JWT_KEY": "test-jwt-key-not-for-production",
    "JWT_SHARE_KEY": "test-share-key-not-for-production",
    "NEO4J_PASSWORD": "TestPassword123",
    "MONGO_PASSWORD": "TestPassword123",
    "MAIL_PASSWORD": "TestPassword123",
    "SHARE_TOKEN_PW": "TestPassword123",
}


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    names = {name.upper() for name in list(validation.REQUIRED_SECRETS) + list(validation.OPTIONAL_SECRETS)}
    for var in list(os.environ):
        if var.upper() in names:
            monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("MITOCUBE_DEV_MODE", "1")


def test_required_secrets_found_uppercase(monkeypatch):
    for key, value in REQUIRED.items():
        monkeypatch.setenv(key, value)
    assert validation.validate_required_secrets() == []


@pytest.mark.parametrize("casing", ["lower", "mixed"])
def test_required_secrets_found_any_casing(monkeypatch, casing):
    for key, value in REQUIRED.items():
        name = key.lower() if casing == "lower" else key.capitalize()
        monkeypatch.setenv(name, value)
    assert validation.validate_required_secrets() == []


def test_required_secrets_found_in_env_file_any_casing(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    lines = [f"{key.lower()}={value}" for key, value in REQUIRED.items()]
    env_file.write_text("\n".join(lines) + "\n")
    monkeypatch.setenv("MITOCUBE_ENV_FILE", str(env_file))
    assert validation.validate_required_secrets() == []


def test_missing_secret_reports_exact_name(monkeypatch):
    for key, value in REQUIRED.items():
        if key != "JWT_SHARE_KEY":
            monkeypatch.setenv(key, value)
    assert validation.validate_required_secrets() == [
        "Missing required secret: JWT_SHARE_KEY"
    ]

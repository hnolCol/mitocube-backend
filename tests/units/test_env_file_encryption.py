import base64
import os

import pytest
from cryptography.fernet import Fernet

from config.secrets.encryption import (
    EnvFileEncryptor,
    PBKDF2_ITERATIONS,
    SALT_HEADER,
    _is_fernet_key,
)


def test_generated_key_roundtrip(tmp_path):
    encryptor = EnvFileEncryptor()
    key = encryptor.get_key()

    assert _is_fernet_key(key)

    env_file = tmp_path / ".env"
    env_file.write_text("JWT_KEY=abc\nDB_PW=secret\n")
    encryptor.encrypt_file(str(env_file), str(tmp_path / ".env.enc"))

    decryptor = EnvFileEncryptor(key)
    decryptor.decrypt_file(str(tmp_path / ".env.enc"), str(tmp_path / ".env.out"))
    assert (tmp_path / ".env.out").read_text() == "JWT_KEY=abc\nDB_PW=secret\n"


def test_passphrase_key_uses_pbkdf2_salt_header():
    encryptor = EnvFileEncryptor("weak-passphrase")
    token = encryptor.encrypt_string("secret-value")

    parts = token.split(":", 2)
    assert len(parts) == 3
    assert parts[0] == SALT_HEADER
    salt = base64.urlsafe_b64decode(parts[1])
    assert len(salt) == 16


def test_passphrase_roundtrip():
    encryptor = EnvFileEncryptor("weak-passphrase")
    token = encryptor.encrypt_string("secret-value")

    decryptor = EnvFileEncryptor("weak-passphrase")
    assert decryptor.decrypt_string(token) == "secret-value"


def test_passphrase_ciphertext_differs_between_encryptions():
    encryptor = EnvFileEncryptor("weak-passphrase")
    token_a = encryptor.encrypt_string("secret-value")
    token_b = encryptor.encrypt_string("secret-value")

    assert token_a != token_b


def test_passphrase_mode_rejects_wrong_passphrase():
    encryptor = EnvFileEncryptor("correct-passphrase")
    token = encryptor.encrypt_string("secret-value")

    with pytest.raises(Exception):
        EnvFileEncryptor("wrong-passphrase").decrypt_string(token)


def test_legacy_padded_ciphertext_still_decrypts():
    legacy_key = "short"
    legacy_fernet = Fernet(
        base64.urlsafe_b64encode(legacy_key.ljust(32)[:32].encode())
    )
    token = legacy_fernet.encrypt(b"legacy-secret").decode()

    decryptor = EnvFileEncryptor(legacy_key)
    assert decryptor.decrypt_string(token) == "legacy-secret"


def test_explicit_fernet_key_used_directly():
    key = Fernet.generate_key().decode()
    encryptor = EnvFileEncryptor(key)
    token = encryptor.encrypt_string("secret-value")

    assert SALT_HEADER not in token
    assert EnvFileEncryptor(key).decrypt_string(token) == "secret-value"


def test_encrypt_file_roundtrip_with_passphrase(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("NEO4J_PASSWORD=pw\n")
    enc_file = tmp_path / ".env.enc"

    EnvFileEncryptor("deploy-passphrase").encrypt_file(str(env_file), str(enc_file))
    out_file = tmp_path / ".env.out"
    EnvFileEncryptor("deploy-passphrase").decrypt_file(str(enc_file), str(out_file))

    assert out_file.read_text() == "NEO4J_PASSWORD=pw\n"


def test_pbkdf2_iteration_count():
    assert PBKDF2_ITERATIONS >= 600_000


def test_is_fernet_key_rejects_short_strings():
    assert not _is_fernet_key("short")
    assert not _is_fernet_key(base64.urlsafe_b64encode(os.urandom(16)).decode())
    assert _is_fernet_key(base64.urlsafe_b64encode(os.urandom(32)).decode())

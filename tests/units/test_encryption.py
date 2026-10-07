from datetime import timedelta

from fastapi import HTTPException
from jose import jwt

from services.encryption import (
    create_access_token,
    create_password_hash,
    create_share_token,
    decode_token,
    verify_password,
    create_hierarchical_hash,
)

TEST_JWT_KEY = "test-jwt-key-not-for-production"
TEST_SHARE_KEY = "test-share-key-not-for-production"


def make_user_token(payload=None):
    import time
    base = {"tag": "abcdefgh", "verified": True, "purpose": "login"}
    if payload:
        base.update(payload)
    base.setdefault("exp", time.time() + 3600)
    return jwt.encode(base, TEST_JWT_KEY, algorithm="HS256")


class TestPasswordHashing:
    def test_hash_is_not_plaintext(self):
        h = create_password_hash("s3cret-pass")
        assert h != "s3cret-pass"
        assert "s3cret-pass" not in h

    def test_hash_contains_bcrypt_prefix(self):
        h = create_password_hash("s3cret-pass")
        assert h.startswith("$2")

    def test_verify_correct_password(self):
        h = create_password_hash("s3cret-pass")
        assert verify_password("s3cret-pass", h) is True

    def test_verify_wrong_password(self):
        h = create_password_hash("s3cret-pass")
        assert verify_password("wrong", h) is False

    def test_salt_is_random(self):
        assert create_password_hash("x") != create_password_hash("x")


class TestCreateAccessToken:
    def test_creates_decodable_token(self, token_settings):
        token = create_access_token({"tag": "abcdefgh"})
        decoded = decode_token(token)
        assert decoded["tag"] == "abcdefgh"

    def test_empty_payload_raises(self, token_settings):
        try:
            create_access_token({})
            assert False, "expected ValueError"
        except ValueError:
            pass

    def test_key_subset_filters_payload(self, token_settings):
        token = create_access_token({"tag": "abcdefgh", "secret_field": "leak"}, key_subset=["tag"])
        decoded = decode_token(token)
        assert decoded.get("secret_field") is None

    def test_key_subset_with_no_overlap_raises(self, token_settings):
        try:
            create_access_token({"tag": "abcdefgh"}, key_subset=["other"])
            assert False, "expected ValueError"
        except ValueError:
            pass

    def test_add_dict_merged(self, token_settings):
        token = create_access_token({"tag": "abcdefgh"}, add_dict={"verified": True})
        decoded = decode_token(token)
        assert decoded["verified"] is True

    def test_expires_delta_respected(self, token_settings):
        token = create_access_token({"tag": "abcdefgh"}, expires_delta=timedelta(minutes=1))
        decoded = decode_token(token)
        assert "exp" in decoded

    def test_share_token_uses_share_key(self, token_settings):
        from datetime import datetime
        token = create_access_token({"tag": "abcdefgh"}, share_token=True)
        decoded = jwt.decode(token, TEST_SHARE_KEY, algorithms=["HS256"])
        assert decoded["tag"] == "abcdefgh"


class TestDecodeToken:
    def test_valid_token(self, token_settings):
        assert decode_token(make_user_token())["tag"] == "abcdefgh"

    def test_expired_token_raises_401(self, token_settings):
        import time
        expired = jwt.encode({"tag": "x", "exp": time.time() - 10}, TEST_JWT_KEY, algorithm="HS256")
        try:
            decode_token(expired)
            assert False, "expected HTTPException"
        except HTTPException as e:
            assert e.status_code == 401

    def test_tampered_token_raises_401(self, token_settings):
        token = make_user_token()[:-3] + "aaa"
        try:
            decode_token(token)
            assert False, "expected HTTPException"
        except HTTPException as e:
            assert e.status_code == 401

    def test_wrong_key_token_raises_401(self, token_settings):
        token = jwt.encode({"tag": "x"}, "attacker-key", algorithm="HS256")
        try:
            decode_token(token)
            assert False, "expected HTTPException"
        except HTTPException as e:
            assert e.status_code == 401

    def test_garbage_token_raises_401(self, token_settings):
        try:
            decode_token("not-a-token")
            assert False, "expected HTTPException"
        except HTTPException as e:
            assert e.status_code == 401

    def test_alg_none_rejected(self, token_settings):
        import base64, json
        header = base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode()).rstrip(b"=")
        payload = base64.urlsafe_b64encode(json.dumps({"tag": "x", "verified": True}).encode()).rstrip(b"=")
        unverified = (header + b"." + payload + b".").decode()
        try:
            decode_token(unverified)
            assert False, "expected HTTPException"
        except HTTPException as e:
            assert e.status_code == 401


class TestHierarchicalHash:
    def test_deterministic(self):
        a = create_hierarchical_hash({"b": 1, "a": 2})
        b = create_hierarchical_hash({"a": 2, "b": 1})
        assert a == b

    def test_different_data_different_hash(self):
        assert create_hierarchical_hash({"a": 1}) != create_hierarchical_hash({"a": 2})

    def test_output_is_sha256_hex(self):
        h = create_hierarchical_hash({"a": 1})
        assert len(h) == 64
        int(h, 16)

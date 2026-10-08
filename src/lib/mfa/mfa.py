# services/mfa/runtime.py
from datetime import datetime, timedelta, timezone
from pymongo import MongoClient, ReturnDocument
from config.settings.token import get_mfa_settings
from lib.ai.agent.config import get_mongo_db_settings
from config.settings.token import get_user_token_settings

mfa_settings = get_mfa_settings()
token_settings = get_user_token_settings()
mongo_db_settings = get_mongo_db_settings()
class MFARuntime:
    def __init__(self) -> None:
        self.client: MongoClient | None = None
        self.attempts = None
        self.challenges = None

    async def startup(self) -> None:
        self.client = MongoClient(mongo_db_settings.AGENT_MONGO_URI)
        db = self.client[mongo_db_settings.MFA_MONGO_DB_NAME]

        self.attempts = db["mfa_attempts"]
        self.attempts.create_index("expires_at", expireAfterSeconds=0)
        self.attempts.create_index("user_tag", unique=True)

        self.challenges = db["mfa_challenges"]
        self.challenges.create_index("expires_at", expireAfterSeconds=0)
        self.challenges.create_index("user_tag", unique=True)

        self.login_attempts = db["login_rate_limit"]
        self.login_attempts.create_index("expires_at", expireAfterSeconds=0)
        self.login_attempts.create_index("key", unique=True)

    def health_check(self) -> bool:
        """Cheap connectivity probe for startup health checks."""
        if self.client is None:
            raise RuntimeError("MFARuntime not started; call startup() first.")
        self.client.admin.command("ping")
        return True

    async def shutdown(self) -> None:
        if self.client is not None:
            self.client.close()

    # --- attempts (unchanged from before) ---
    def register_failure(self, user_tag: str) -> int:
        now = datetime.now(timezone.utc)
        doc = self.attempts.find_one_and_update(
            {"user_tag": user_tag},
            {
                "$inc": {"count": 1},
                "$setOnInsert": {"first_failure_at": now},
                "$set": {"expires_at": now + timedelta(minutes=mfa_settings.MFA_LOCKOUT_MINUTES)},
            },
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        return doc["count"]

    def get_failure_count(self, user_tag: str) -> int:
        doc = self.attempts.find_one({"user_tag": user_tag})
        return doc["count"] if doc else 0

    def is_locked_out(self, user_tag: str) -> bool:
        return self.get_failure_count(user_tag) >= mfa_settings.MFA_MAX_ATTEMPTS

    def reset_attempts(self, user_tag: str) -> None:
        self.attempts.delete_one({"user_tag": user_tag})

    # --- challenges (new: the actual verification code) ---
    def store_challenge(self, user_tag: str, code: str, ttl : timedelta) -> None:
        now = datetime.now(timezone.utc)
        self.challenges.find_one_and_update(
            {"user_tag": user_tag},
            {"$set": {
                "code": code,
                "created_at": now,
                "expires_at": now + ttl,
            }},
            upsert=True,
        )

    def get_challenge_code(self, user_tag: str) -> str | None:
        doc = self.challenges.find_one({"user_tag": user_tag})
        return doc["code"] if doc else None

    def clear_challenge(self, user_tag: str) -> None:
        self.challenges.delete_one({"user_tag": user_tag})

    # --- login rate limiting (password step of /api/auth/token/) ---
    def register_login_failure(self, key: str) -> int:
        """Counts a failed login attempt for the given key (email or IP).

        The window resets when the document expires (Mongo TTL index), so
        the counter naturally clears itself after the configured window.
        Returns the attempt count within the current window.
        """
        now = datetime.now(timezone.utc)
        doc = self.login_attempts.find_one_and_update(
            {"key": key},
            {
                "$inc": {"count": 1},
                "$setOnInsert": {"first_failure_at": now},
                "$set": {"expires_at": now + timedelta(minutes=mfa_settings.LOGIN_RATE_LIMIT_WINDOW_MINUTES)},
            },
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        return doc["count"]

    def get_login_failure_count(self, key: str) -> int:
        doc = self.login_attempts.find_one({"key": key})
        return doc["count"] if doc else 0

    def is_login_rate_limited(self, key: str) -> bool:
        return self.get_login_failure_count(key) >= mfa_settings.LOGIN_RATE_LIMIT_MAX_ATTEMPTS

    def reset_login_failures(self, key: str) -> None:
        self.login_attempts.delete_one({"key": key})

mfa_runtime = MFARuntime()
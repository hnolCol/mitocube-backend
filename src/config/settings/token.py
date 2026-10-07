from datetime import datetime, timedelta
from functools import lru_cache

from pydantic_settings import BaseSettings 
from pydantic import SecretStr

class UserToken(BaseSettings):
    """BaseSettings for a user token"""
    expires_after_hours : timedelta = timedelta(hours=48)
    expires_after_minutes : timedelta = timedelta(minutes=15)
    jwt_key : SecretStr 
    jwt_algorithm : str = "HS256"

    class Config:
        env_file = ".env"
        extra = "ignore"


class ShareToken(BaseSettings):
    """
    Share tokens are used to push performance data
    or datasets to the application.
    The BaseSettings define the security settings. 
    """
    expires_after_hours : timedelta = timedelta(days = 120) #4 months 
    jwt_share_key : SecretStr 
    share_token_pw : SecretStr
    jwt_algorithm : str = "HS256"

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_user_token_settings():
    return UserToken()

@lru_cache()
def get_share_token_settings():
    return ShareToken()


class MFASettings(BaseSettings):
    MFA_MONGO_DB_NAME: str = "mfa_db"
    MFA_MAX_ATTEMPTS: int = 5
    MFA_LOCKOUT_MINUTES: int = 15
    MFA_ENCRYPTION_KEY: SecretStr 
    LOGIN_RATE_LIMIT_MAX_ATTEMPTS: int = 10
    LOGIN_RATE_LIMIT_WINDOW_MINUTES: int = 10
    # Comma-separated list of reverse-proxy IPs whose X-Forwarded-For
    # header may be trusted (production runs behind nginx).
    TRUSTED_PROXY_IPS: str = "127.0.0.1,::1"
   
    class Config:
        env_file = ".env"
        extra = "ignore"

def get_mfa_settings() -> MFASettings:
    return MFASettings()
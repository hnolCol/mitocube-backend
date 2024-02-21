from datetime import datetime, timedelta
from functools import lru_cache

from pydantic_settings import BaseSettings 
from pydantic import SecretStr

class UserToken(BaseSettings):
    """BaseSettings for a user token"""
    expires_after_hours : timedelta = timedelta(hours=48)
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
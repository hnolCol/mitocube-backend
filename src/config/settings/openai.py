
from functools import lru_cache

from pydantic_settings import BaseSettings


class OpenAI(BaseSettings):
    """Base Settings"""

    open_ai_api_key : str

    class Config:
        env_file = ".env"
        extra = "ignore"

@lru_cache()
def get_open_ai_settings():
    return OpenAI()
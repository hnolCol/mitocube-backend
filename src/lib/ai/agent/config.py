"""Central settings, env-driven so you don't hardcode model choice or paths."""

import os
from dataclasses import dataclass
from functools import lru_cache

from pydantic_settings import BaseSettings 

class Settings(BaseSettings):
    MONGO_USER: str = "ai"
    MONGO_PASSWORD: str = os.environ.get("MONGO_PASSWORD", "password")
    MONGO_HOST: str = "localhost"
    MONGO_PORT: int = 27017
    MONGO_AUTH_DB: str = "admin"

    AGENT_MONGO_DB_NAME: str = os.environ.get("AGENT_MONGO_DB_NAME", "mongodb")
    MFA_MONGO_DB_NAME: str = os.environ.get("MFA_MONGO_DB_NAME", "auth")

    @property
    def AGENT_MONGO_URI(self) -> str:
        return (
            f"mongodb://{self.MONGO_USER}:{self.MONGO_PASSWORD}"
            f"@{self.MONGO_HOST}:{self.MONGO_PORT}"
            f"/?authSource={self.MONGO_AUTH_DB}"
        )
    class Config:
        env_file = ".env"
        extra = "ignore"

@lru_cache
def get_mongo_db_settings() -> Settings:
    return Settings()
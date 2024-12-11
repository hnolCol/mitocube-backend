from datetime import datetime, timedelta
from functools import lru_cache
from typing import List 
from pydantic_settings import BaseSettings 
from pydantic import SecretStr

class Unit(BaseSettings):
    """BaseSettings for a user token"""
    units: List[str] = "mass","concentration", "time","temperature","volume","masstocharge","voltage","flow rate","arbitrary","feature","length","fraction"

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_units_settings():
    return Unit()

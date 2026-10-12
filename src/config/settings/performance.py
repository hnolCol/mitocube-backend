from functools import lru_cache
from pydantic_settings import BaseSettings
from config.settings.env import get_env_file 


class PerformanceSettings(BaseSettings):
    
    class Config:
        env_file = get_env_file()
        extra = "ignore"
    
@lru_cache()
def get_performance_settings():
    return PerformanceSettings()
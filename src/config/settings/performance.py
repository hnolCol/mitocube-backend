from functools import lru_cache
from pydantic_settings import BaseSettings 


class PerformanceSettings(BaseSettings):
    
    class Config:
        env_file = ".env"
        extra = "ignore"
    
@lru_cache()
def get_performance_settings():
    return PerformanceSettings()
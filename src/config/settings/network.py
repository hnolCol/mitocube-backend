from functools import lru_cache

from pydantic_settings import BaseSettings 
from pydantic import EmailStr, DirectoryPath, HttpUrl

from typing import List

class Network(BaseSettings):
    
    network_dir : DirectoryPath
    
    class Config:
        env_file = ".env"
        extra = "ignore"
    
@lru_cache()
def get_network_settings():
    return Network()
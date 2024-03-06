from functools import lru_cache

from pydantic_settings import BaseSettings 
from pydantic import EmailStr, DirectoryPath, HttpUrl

from typing import List

class Network(BaseSettings):
    
    network_dir : DirectoryPath =  "/Users/hnolte/Documents/GitHub/mitocube-backend/resources/network"  
    
    
@lru_cache()
def get_network_settings():
    return Network()
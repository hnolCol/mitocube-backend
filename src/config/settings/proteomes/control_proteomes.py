# Proteomes are generally added via the GUI/FastAPI request. 
# However to make control proteins available for selection, there 
# is a file with certain proteins such as GFP, scrambled (fake entry), LucZ
# to make them available without the specific proteome. 

from functools import lru_cache

from pydantic_settings import BaseSettings
from config.settings.env import get_env_file 
from pydantic import FilePath

from typing import List

class Proteomes(BaseSettings):
    add_control_proteome : bool = True 
    control_proteome_file : FilePath
    

    class Config:
        env_file = get_env_file()
        extra = "ignore"
        
@lru_cache
def get_control_proteome_settings():
    return Proteomes()
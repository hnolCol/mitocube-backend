# Proteomes are generally added via the GUI/FastAPI request. 
# However to make control proteins available for selection, there 
# is a file with certain proteins such as GFP, scrambled (fake entry), LucZ
# to make them available without the specific proteome. 

from functools import lru_cache

from pydantic_settings import BaseSettings 
from pydantic import FilePath

from typing import List

class Proteomes(BaseSettings):
    add_control_proteome : bool = True 
    control_proteome_file : FilePath = "/Users/PParsa/Documents/GitHub/mitocube-backend/resources/features/controls/data.txt"
    

    class Config:
        env_file = ".env"
        extra = "ignore"
        
@lru_cache
def get_control_proteome_settings():
    return Proteomes()
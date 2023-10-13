from functools import lru_cache

from pydantic_settings import BaseSettings 
from pydantic import SecretStr, EmailStr

from typing import List

class General(BaseSettings):
    """Class model for general settings"""
    app_name : str = "MitoCube"
    version : str = "0.1"
    lead_contact : EmailStr = "h.nolte@age.mpg.de"
    description : str = "MitoCube offers protein-centric searches to explore the expression of a protein in all acquired proteomic datasets."
    allowed_email_domains : List[str] = ["@uni-koeln.de","@age.mpg.de","@uni-bonn.de"]
    # class Config:
    #     env_file = ".env"
    #     case_sensitive = True



@lru_cache()
def get_general_settings():
    """
    Return General Base Settings using caching 
    (env file is otherwise loaded everytime.)
    """
    return General()
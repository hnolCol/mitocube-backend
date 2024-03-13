from functools import lru_cache

from pydantic_settings import BaseSettings 
from pydantic import EmailStr, DirectoryPath, HttpUrl, FilePath

from typing import List

class General(BaseSettings):
    """Class model for general settings"""
    app_name : str = "MitoCube"
    version : str = "0.1"
    url : HttpUrl = "https://app.mitocube.com"
    lead_contact_first_name : str = "Hendrik"
    lead_contact_last_name : str = "Nolte"
    lead_contact_institute : str = "Max Planck Istitute for Biology of Ageing"
    lead_contact_group : str = "Department of Mitochondrial Proteostasis"
    lead_contact : EmailStr = "h.nolte@age.mpg.de"
    description : str = "MitoCube offers protein-centric searches to explore the expression of a protein in all acquired proteomic datasets."
    allowed_email_domains : List[str] = ["@uni-koeln.de","@age.mpg.de","@uni-bonn.de","@instantclue.de"]

    frontend_build : DirectoryPath = "/Users/hnolte/Documents/GitHub/mitocube-frontend/dist"
    frontend_build_assets : DirectoryPath = "/Users/hnolte/Documents/GitHub/mitocube-frontend/dist/assets"
    
    use_terms_file : FilePath = "/Users/hnolte/Documents/GitHub/mitocube-backend/resources/terms/usage.json"
    
    class Config:
         env_file = ".env"
         case_sensitive = True
         extra = "ignore"



@lru_cache()
def get_general_settings():
    """
    Return General Base Settings using caching 
    (env file is otherwise loaded everytime.)
    """
    return General()

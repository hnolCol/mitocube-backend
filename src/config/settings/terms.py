from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import FilePath

class UseTerms(BaseSettings):
    
    required_acceptance_to_login : bool = False
    path_to_use_terms : Optional[FilePath] = None 
    
    
    
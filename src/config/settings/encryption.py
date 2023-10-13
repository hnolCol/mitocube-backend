from pydantic_settings import BaseSettings
from typing import Literal 

class Encryption(BaseSettings):
    """
    Settings for encryption
    
    Encryption is using default setting of passlib otherwise 
    including auto generated salt and specified rounds.
    """
    hash_algorithm : Literal["bcrypt","pbkdf2_sha256","pbkdf2_sha512"] = "bcrypt"

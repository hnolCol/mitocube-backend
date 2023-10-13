from functools import lru_cache

from pydantic_settings import BaseSettings
from pydantic import EmailStr 


class User(BaseSettings):
    """User Settings. Defines the attribute that are required
    upon user registration. 
    Please note that changing the settings here you also have 
    to adapt the pydantic / DB user model"""
    email : EmailStr 
    firstname : str 
    lastname : str 
    institute : str 
    research_group : str    


@lru_cache()
def get_users_settings():
    return User()


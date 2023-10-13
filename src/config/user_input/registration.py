
from pydantic_settings import BaseSettings 


from pydantic import EmailStr 

class UserRegistration(BaseSettings):

    user_email : str
    email : EmailStr 

from pydantic import BaseModel 
from pydantic import EmailStr 
from typing import Optional 

class InfoResponse(BaseModel):
    """BaseModel for a web application info"""
    app_name : str
    app_description : str
    version : str 
    use_terms : Optional[str] = None 
    lead_contact : EmailStr



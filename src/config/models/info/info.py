from pydantic import BaseModel 

from pydantic import EmailStr 


class InfoResponse(BaseModel):
    """BaseModel for a web applicaion info"""
    app_name : str
    app_description : str
    version : str 
    lead_contact : EmailStr



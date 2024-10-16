from pydantic import BaseModel, EmailStr

class BasePRM(BaseModel):  # PRM ~ Pydantic Response Model
    """Base Pydantic Response Model (PRM). Allows to include a message (msg) that can be displayed by the gui"""
    msg: str | None = None


class ApplicationInformationPRM(BasePRM):
    app_name : str
    app_description : str
    version : str
    lead_contact : EmailStr

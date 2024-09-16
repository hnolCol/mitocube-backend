from pydantic import BaseModel

class ApplicationInformationPModel(BaseModel):
    backend_version: str
    something: str

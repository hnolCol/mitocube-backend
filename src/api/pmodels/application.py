from pydantic import BaseModel

class BasePRM(BaseModel):  # PRM ~ Pydantic Response Model
    """Base Pydantic Response Model (PRM). Allows to include a message (msg) that can be displayed by the gui"""
    msg: str | None = None


class ApplicationInformationPModel(BasePRM):
    backend_version: str
    something: str

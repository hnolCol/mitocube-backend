from pydantic import BaseModel, field_validator
from typing import Literal


class ProteomeModel(BaseModel):
    """BaseModel for a Proteome defined by upid (Uniprot ID)"""
    upid : str 
    domain : Literal["Bacteria", "Archaea", "Eukaryota"]
    name : str 

    @field_validator("upid")
    @classmethod
    def check_UPID(cls, value : str) -> str:
        if not value.startswith("UP"):
            raise ValueError("upid proteome identifier must start with UP.")
        return value 

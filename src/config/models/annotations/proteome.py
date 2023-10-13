from pydantic import BaseModel, validator
from typing import Literal


class Proteome(BaseModel):
    """BaseModel for a Proteome defined by upid (Uniprot ID)"""
    upid : str 
    domain : Literal["Bacteria","Archaea","Eukaryota"]
    name : str 

    @validator("upid", pre=True)
    def check_UPID(cls, value : str) -> str:
        if not value.startswith("UP"):
            raise ValueError("upid proteome identifier must start with UP.")
        return value 
    




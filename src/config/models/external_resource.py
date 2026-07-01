from pydantic import BaseModel, model_validator
from typing import Optional
from services.encryption import create_hierarchical_hash


class ExternalResourceInsertModel(BaseModel):
    title: str
    link: str
    doi: Optional[str] = None
    type: str = "publication" 
    tag: str = ""

    @model_validator(mode="after")
    def generate_tag(self):
        self.tag = create_hierarchical_hash([self.title, self.link])[:20]
        return self


class ExternalResourceModel(BaseModel):
    tag: str
    title: str
    link: str
    doi: Optional[str] = None
    type: str
    created_at: Optional[int] = None
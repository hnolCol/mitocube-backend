from pydantic import BaseModel, model_validator
from typing import Optional, List
from services.encryption import create_hierarchical_hash
from config.models.attributes import AttributeTree


class ExternalResourceInsertModel(BaseModel):
    title: str
    link: Optional[str] = None
    doi: Optional[str] = None
    type: str = "crosslink_resource"
    author: Optional[str] = None
    publication_date: Optional[str] = None
    is_external: bool
    condition_applications: Optional[List[AttributeTree]] = None
    tag: str = ""

    @model_validator(mode="after")
    def generate_tag(self):
        self.tag = create_hierarchical_hash([self.title, self.link or ""])[:20]
        return self


class ExternalResourceModel(BaseModel):
    tag: str
    title: str
    link: Optional[str] = None
    author: Optional[str] = None
    publication_date: Optional[str] = None
    doi: Optional[str] = None
    type: str
    external: Optional[bool] = None
    created_at: Optional[int] = None
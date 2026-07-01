from pydantic import BaseModel, model_validator
from typing import Optional
from services.encryption import create_hierarchical_hash


class CrosslinkInsertModel(BaseModel):
    protein_tag_a: str
    protein_tag_b: str
    pos_a: int
    pos_b: int
    peptide_a: Optional[str] = None
    peptide_b: Optional[str] = None
    score: Optional[float] = None
    tag: str = ""

    @model_validator(mode="after")
    def generate_tag(self):
        self.tag = create_hierarchical_hash([
            self.protein_tag_a, self.protein_tag_b,
            str(self.pos_a), str(self.pos_b)
        ])[:20]
        return self


class CrosslinkModel(BaseModel):
    tag: str
    protein_tag_a: str
    protein_tag_b: str
    pos_a: int
    pos_b: int
    peptide_a: Optional[str] = None
    peptide_b: Optional[str] = None
    score: Optional[float] = None
    created_at: Optional[int] = None
    resource_tag: Optional[str] = None
    resource_title: Optional[str] = None
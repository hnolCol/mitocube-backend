from pydantic import BaseModel, Field, model_validator
from typing import Optional, List, Literal
from config.models.attributes import MinimalTraitModel
from services.random_generators import get_random_string


class AttributeProposalModel(BaseModel):
    """The attribute and optional traits a user proposes."""
    text: str
    abbr: Optional[str] = None
    group_tags: List[str] = []
    priority: int = 500
    traits: List[MinimalTraitModel] = []


class TraitProposalModel(BaseModel):
    """A trait proposed for an existing attribute."""
    attribute_tag: str
    text: str
    description: Optional[str] = ""
    priority: int = 500


class AttributeRequestInsertModel(BaseModel):
    """A user request to add a new attribute (optionally with traits)
    or a new trait to an existing attribute."""
    kind: Literal["attribute", "trait"]
    attribute: Optional[AttributeProposalModel] = None
    trait: Optional[TraitProposalModel] = None
    comment: Optional[str] = None

    @model_validator(mode="after")
    def check_payload(self):
        if self.kind == "attribute" and self.attribute is None:
            raise ValueError("The attribute proposal is required for kind='attribute'.")
        if self.kind == "trait" and self.trait is None:
            raise ValueError("The trait proposal is required for kind='trait'.")
        if self.kind == "trait" and len(self.trait.attribute_tag.strip()) == 0:
            raise ValueError("The trait proposal requires an attribute_tag.")
        return self


class AttributeRequestStatusModel(BaseModel):
    tag: str
    status: Literal["pending", "accepted", "rejected"]
    reviewer_tag: Optional[str] = None
    reviewed_at: Optional[float] = None
    review_comment: Optional[str] = None


class AttributeRequestModel(BaseModel):
    tag: str = Field(default_factory=lambda: get_random_string(N=12))
    kind: Literal["attribute", "trait"]
    status: Literal["pending", "accepted", "rejected"] = "pending"
    user_tag: str
    comment: Optional[str] = None
    created_at: Optional[float] = None
    attribute: Optional[AttributeProposalModel] = None
    trait: Optional[TraitProposalModel] = None


class AttributeRequestReviewModel(BaseModel):
    comment: Optional[str] = None


class DepositionRequestInsertModel(BaseModel):
    """A user request that a submission's data should be deposited to an
    external database (e.g. PRIDE)."""
    submission_tag: str
    database: str
    comment: Optional[str] = None


class DepositionRequestModel(BaseModel):
    tag: str = Field(default_factory=lambda: get_random_string(N=12))
    submission_tag: str
    status: Literal["pending", "deposited", "rejected"] = "pending"
    user_tag: str
    database: str
    comment: Optional[str] = None
    created_at: Optional[float] = None
    identifier: Optional[str] = None
    url: Optional[str] = None
    token: Optional[str] = None
    reviewer_tag: Optional[str] = None
    reviewed_at: Optional[float] = None
    review_comment: Optional[str] = None


class DepositionRequestCompleteModel(BaseModel):
    """The deposition information added by a curator once the data have
    been deposited to the external database."""
    identifier: str
    url: Optional[str] = None
    token: Optional[str] = None
    comment: Optional[str] = None


class DepositionRequestReviewModel(BaseModel):
    comment: Optional[str] = None

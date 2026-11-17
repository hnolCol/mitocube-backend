from typing import List, Optional

from pydantic import BaseModel, Field

from config.enums.users.pats import PATScopeEnum


class PATInsertModel(BaseModel):
    """Properties for creating a new personal access token."""
    name : str = Field(..., description="Human readable name, e.g. 'qc-upload-lab-PC3'")
    scopes : List[PATScopeEnum] = Field(..., description="Scopes granted to the token")
    expires_in_days : int = Field(default=365, ge=1, le=3650)


class PATResponseModel(BaseModel):
    """Metadata of a personal access token. The token itself is only shown once at creation."""
    tag : str
    name : str
    scopes : List[PATScopeEnum]
    created_at : int
    expires_at : int
    last_used_at : Optional[int] = None
    revoked : bool
    revoked_by : Optional[str] = None
    revoked_at : Optional[int] = None


class PATCreationBlockModel(BaseModel):
    """Body for toggling the personal access token creation of a user."""
    blocked : bool


class PATCreatedResponseModel(PATResponseModel):
    """Response after creating a personal access token. Contains the plain token exactly once."""
    token : str

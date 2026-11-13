from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum



class ModularProcedureStatusEnum(str, Enum):
    "Lifecycle status of a modular procedure."
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"



class ModularProcedureBaseModel(BaseModel):
    tag : str
    title : str
    description : str
    status : ModularProcedureStatusEnum = ModularProcedureStatusEnum.DRAFT
    version : int = 1
    content_hash : Optional[str] = None
    user_tag : str
    created_at : Optional[float] = None
    published_at : Optional[float] = None
    condition_application_tags : List[str] = Field(default_factory=list)
    protocol_tags : List[str] = Field(default_factory=list)



class InsertModularProcedureModel(BaseModel):
    title : str
    description : str
    condition_application_tags : List[str] = Field(default_factory=list)
    protocol_tags : List[str] = Field(default_factory=list)



class UpdateModularProcedureModel(BaseModel):
    title : str
    description : str
    condition_application_tags : List[str] = Field(default_factory=list)
    protocol_tags : List[str] = Field(default_factory=list)



class PublishModularProcedureModel(BaseModel):
    tag : str
    version : int
    content_hash : str



class ModularProcedureSubmissionModel(BaseModel):
    "A submission linked to a modular procedure."
    procedure_tag : str
    submission_tag : str
    position : int
    created_at : Optional[float] = None
    done : bool = False
    done_at : Optional[float] = None
    done_by : Optional[str] = None

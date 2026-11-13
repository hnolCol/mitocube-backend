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
    lineage_tag : Optional[str] = None
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



class ExecutionInputWellModel(BaseModel):
    "An input plate well of a procedure execution with its samples and the output wells it is transferred to."
    position : str
    sample_tags : List[str] = Field(default_factory=list)
    output_positions : List[str] = Field(default_factory=list)



class ExecutionOutputWellModel(BaseModel):
    "An output plate well of a procedure execution with its condition applications."
    position : str
    condition_application_tags : List[str] = Field(default_factory=list)



class InsertProcedureExecutionModel(BaseModel):
    "The user input to execute a published modular procedure on a set of samples."
    input_plate_tag : str
    output_plate_tag : str
    input_wells : List[ExecutionInputWellModel] = Field(default_factory=list)
    output_wells : List[ExecutionOutputWellModel] = Field(default_factory=list)



class ProcedureExecutionInputWellModel(BaseModel):
    "A stored input well of a procedure execution."
    position : str
    row_index : int
    column_index : int
    sample_tags : List[str] = Field(default_factory=list)
    output_positions : List[str] = Field(default_factory=list)



class ProcedureExecutionOutputWellModel(BaseModel):
    "A stored output well of a procedure execution. The sample tags are derived from the transfer map (pooling and splitting supported)."
    position : str
    row_index : int
    column_index : int
    sample_tags : List[str] = Field(default_factory=list)
    condition_application_tags : List[str] = Field(default_factory=list)



class ProcedureExecutionModel(BaseModel):
    "A concrete execution of a published modular procedure on a set of samples, mapping input plate wells to output plate wells."
    tag : str
    procedure_tag : str
    input_plate_tag : str
    output_plate_tag : str
    user_tag : str
    created_at : Optional[float] = None
    done_submission_tags : List[str] = Field(default_factory=list)
    input_wells : List[ProcedureExecutionInputWellModel] = Field(default_factory=list)
    output_wells : List[ProcedureExecutionOutputWellModel] = Field(default_factory=list)

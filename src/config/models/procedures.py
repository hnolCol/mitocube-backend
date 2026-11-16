from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from enum import Enum

from config.models.attributes import AttributeTree



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
    """Tags of existing condition applications to reuse."""
    condition_application_trees : List[AttributeTree] = Field(default_factory=list)
    """New condition applications defined as hierarchical attribute/trait trees (like when inserting a submission)."""
    protocol_tags : List[str] = Field(default_factory=list)


class UpdateModularProcedureModel(BaseModel):
    title : str
    description : str
    condition_application_tags : List[str] = Field(default_factory=list)
    condition_application_trees : List[AttributeTree] = Field(default_factory=list)
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



class ExecutionWellMetricModel(BaseModel):
    "A measured value of a single output well: the trait defines the measured quantity (e.g. u g/uL of the concentration attribute)."
    position : str
    trait_tag : str
    value : float



class ProcedureExecutionWellMetricModel(BaseModel):
    "A stored well metric of a procedure execution: a value that is an instance of a trait (like condition values)."
    trait_tag : str
    attribute_tag : Optional[str] = None
    value : float



class InsertProcedureExecutionModel(BaseModel):
    """The user input to execute a published modular procedure on a set of samples.
    The responsible user defaults to the executing user; well metrics map measured
    attributes (e.g. protein concentration) to output wells."""
    input_plate_tag : str
    output_plate_tag : str
    responsible_user_tag : Optional[str] = None
    input_wells : List[ExecutionInputWellModel] = Field(default_factory=list)
    output_wells : List[ExecutionOutputWellModel] = Field(default_factory=list)
    output_well_metrics : List[ExecutionWellMetricModel] = Field(default_factory=list)  # [{position, trait_tag, value}]



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
    metrics : List[ProcedureExecutionWellMetricModel] = Field(default_factory=list)



class ProcedureExecutionModel(BaseModel):
    "A concrete execution of a published modular procedure on a set of samples, mapping input plate wells to output plate wells."
    tag : str
    procedure_tag : str
    input_plate_tag : str
    output_plate_tag : str
    user_tag : str
    responsible_user_tag : Optional[str] = None
    created_at : Optional[float] = None
    done_submission_tags : List[str] = Field(default_factory=list)
    input_wells : List[ProcedureExecutionInputWellModel] = Field(default_factory=list)
    output_wells : List[ProcedureExecutionOutputWellModel] = Field(default_factory=list)

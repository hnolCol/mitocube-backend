from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from enum import Enum

from config.models.attributes import AttributeTree
from config.enums.states import SubmissionStatesEnums


SUBMISSION_STATE_CHOICES = [state.name for state in SubmissionStatesEnums]



class ModularProcedureStatusEnum(str, Enum):
    "Lifecycle status of a modular procedure."
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"


class ProcedureExecutionStatusEnum(str, Enum):
    """Lifecycle status of a procedure execution. Executions start RUNNING and are closed by an explicit
    confirmation (SUCCEEDED, FAILED or ABORTED) that frees the linked submissions for the next module."""
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    ABORTED = "ABORTED"


class ProcedureExecutionOutcomeEnum(str, Enum):
    "The confirmation outcome of a running procedure execution."
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    ABORTED = "ABORTED"



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
    input_plate_format : Optional[str] = None
    """Required container format of the input plate (e.g. '8x12' for a 96 well plate). None means unconstrained."""
    input_plate_type : Optional[str] = None
    """Required plate type of the input plate (e.g. a PCR strip). None means unconstrained."""
    output_plate_format : Optional[str] = None
    output_plate_type : Optional[str] = None
    input_attribute_tags : List[str] = Field(default_factory=list)
    """Attributes whose values may be entered per input well before the execution (e.g. protein concentration)."""
    output_attribute_tags : List[str] = Field(default_factory=list)
    """Attributes for which data are expected on the output wells of a successful execution."""
    success_submission_state : Optional[str] = None
    """Optional submission state (name of SubmissionStatesEnums, e.g. 'PROCESSED') that is set automatically for the linked submissions when an execution is confirmed successful."""



class InsertModularProcedureModel(BaseModel):
    title : str
    description : str
    condition_application_tags : List[str] = Field(default_factory=list)
    """Tags of existing condition applications to reuse."""
    condition_application_trees : List[AttributeTree] = Field(default_factory=list)
    """New condition applications defined as hierarchical attribute/trait trees (like when inserting a submission)."""
    protocol_tags : List[str] = Field(default_factory=list)
    input_plate_format : Optional[str] = None
    input_plate_type : Optional[str] = None
    output_plate_format : Optional[str] = None
    output_plate_type : Optional[str] = None
    input_attribute_tags : List[str] = Field(default_factory=list)
    output_attribute_tags : List[str] = Field(default_factory=list)
    success_submission_state : Optional[str] = None


class UpdateModularProcedureModel(BaseModel):
    title : str
    description : str
    condition_application_tags : List[str] = Field(default_factory=list)
    condition_application_trees : List[AttributeTree] = Field(default_factory=list)
    protocol_tags : List[str] = Field(default_factory=list)
    input_plate_format : Optional[str] = None
    input_plate_type : Optional[str] = None
    output_plate_format : Optional[str] = None
    output_plate_type : Optional[str] = None
    input_attribute_tags : List[str] = Field(default_factory=list)
    output_attribute_tags : List[str] = Field(default_factory=list)
    success_submission_state : Optional[str] = None



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
    side : str = "OUTPUT"
    "The side of the plate the well belongs to: INPUT (values entered before the execution) or OUTPUT (data measured after the execution)."



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
    input_well_metrics : List[ExecutionWellMetricModel] = Field(default_factory=list)
    """Values of the declared input attributes per input well (e.g. the concentration of each sample before harmonization)."""


class FinishProcedureExecutionModel(BaseModel):
    """The confirmation of a running procedure execution: the outcome closes the execution and frees the linked
    submissions for the next module. Only SUCCEEDED triggers the optional submission state change and the adoption
    of the condition applications by the submissions."""
    outcome : ProcedureExecutionOutcomeEnum
    comment : Optional[str] = None



class ProcedureExecutionInputWellModel(BaseModel):
    "A stored input well of a procedure execution."
    position : str
    row_index : int
    column_index : int
    sample_tags : List[str] = Field(default_factory=list)
    output_positions : List[str] = Field(default_factory=list)
    metrics : List[ProcedureExecutionWellMetricModel] = Field(default_factory=list)



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
    status : ProcedureExecutionStatusEnum = Field(default=ProcedureExecutionStatusEnum.RUNNING)
    finished_at : Optional[float] = None
    finished_by : Optional[str] = None
    finish_comment : Optional[str] = None
    done_submission_tags : List[str] = Field(default_factory=list)
    input_well_metrics : List[ProcedureExecutionWellMetricModel] = Field(default_factory=list)
    input_wells : List[ProcedureExecutionInputWellModel] = Field(default_factory=list)
    output_wells : List[ProcedureExecutionOutputWellModel] = Field(default_factory=list)

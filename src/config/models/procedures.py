from pydantic import BaseModel, field_validator, Field
from typing import List, Optional, Dict
from enum import Enum

from config.models.attributes import AttributeTree
from config.enums.states import SubmissionStatesEnums


SUBMISSION_STATE_CHOICES = [state.name for state in SubmissionStatesEnums]



class ModularProcedureStatusEnum(str, Enum):
    """Lifecycle status of a modular procedure: drafts are editable, publishing freezes the
    content with a SHA-256 hash, retiring keeps the published procedure (and the reproducibility
    of its executions) forever but indicates it can no longer be assigned or executed."""
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    RETIRED = "RETIRED"


class ProcedureExecutionStatusEnum(str, Enum):
    """Lifecycle status of a procedure execution. Executions start RUNNING and are closed by an explicit
    confirmation (SUCCEEDED, FAILED or ABORTED) that frees the linked submissions for the next module."""
    RUNNING = "RUNNING"
    DRAFT = "DRAFT"
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
    required_submission_state : Optional[str] = None
    """Optional submission state (name of SubmissionStatesEnums, e.g. 'SUBMITTED' for state 0) that the linked submissions must be in: only submissions in this state are offered when setting up an execution. None means unconstrained."""
    pubmed_ids : List[str] = Field(default_factory=list)
    """PubMed IDs of the publications this procedure is based on or referenced by."""
    min_output_wells_per_sample : int = 1
    """Minimum number of output wells each sample is transferred to per execution: 1 means the
    module mirrors the sample numbers; larger values describe a fixed or minimal duplication of
    the samples (e.g. 8 for an 8-fraction fractionation)."""
    max_output_wells_per_sample : Optional[int] = None
    """Maximum number of output wells per sample; None means unbounded. min == max fixes the
    number exactly (e.g. min = max = 8 for exactly 8 fractions)."""


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
    required_submission_state : Optional[str] = None
    pubmed_ids : List[str] = Field(default_factory=list)
    min_output_wells_per_sample : int = 1
    max_output_wells_per_sample : Optional[int] = None


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
    required_submission_state : Optional[str] = None
    pubmed_ids : List[str] = Field(default_factory=list)
    min_output_wells_per_sample : int = 1
    max_output_wells_per_sample : Optional[int] = None



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



class ExecutionStateModel(BaseModel):
    "A state of a procedure execution in its state history: the state itself, when it was set and by whom."
    state : str
    created_at : Optional[float] = None
    user_tag : Optional[str] = None


class SampleLocationWellModel(BaseModel):
    "A well of a procedure execution holding the sample, on the input or output plate."
    plate_tag : str
    position : str
    side : str


class SampleLocationModel(BaseModel):
    """The current location of a sample: the wells of its most recent procedure execution
    (a sample stays where the last execution placed it, even if that execution failed)."""
    sample_tag : str
    procedure_tag : str
    execution_tag : str
    execution_status : str = "RUNNING"
    created_at : Optional[float] = None
    wells : List[SampleLocationWellModel] = Field(default_factory=list)


class ExecutionSummaryModel(BaseModel):
    "Summary of a procedure execution for the overview listing: the header data and well counts."
    tag : str
    procedure_tag : str
    """The plate tags are None while the (draft) execution has no plates in its design yet —
    drafts appear in the overview listing without a saved design."""
    input_plate_tag : Optional[str] = None
    output_plate_tag : Optional[str] = None
    user_tag : str
    responsible_user_tag : Optional[str] = None
    created_at : Optional[float] = None
    status : ProcedureExecutionStatusEnum = Field(default=ProcedureExecutionStatusEnum.RUNNING)
    wells_blocked : bool = True
    finished_at : Optional[float] = None
    finished_by : Optional[str] = None
    finish_comment : Optional[str] = None
    done_submission_tags : List[str] = Field(default_factory=list)
    n_input_wells : int = 0
    n_output_wells : int = 0


def split_well_ref(ref, default_plate_tag=None):
    """Splits a well reference into ``(plate_tag, position)``: the transfer map may target wells
    on several plates of one side, so a reference is either a plain position (e.g. ``A1`` - the
    primary plate of that side) or plate-qualified (``plate_tag:A1``)."""
    if isinstance(ref, str) and ":" in ref:
        plate_tag, position = ref.split(":", 1)
        return plate_tag, position
    return (default_plate_tag, ref)


class ExecutionInputWellModel(BaseModel):
    """An input plate well of a procedure execution with its samples and the output wells it is
    transferred to. `plate_tag` is the input plate the well is on (None: the primary input plate)."""
    position : str
    plate_tag : Optional[str] = None
    sample_tags : List[str] = Field(default_factory=list)
    output_positions : List[str] = Field(default_factory=list)
    """Output wells this input well is transferred to: plain positions (primary output plate) or
    plate-qualified refs ("plate_tag:A1" for the additional output plates)."""



class ExecutionOutputWellModel(BaseModel):
    """An output plate well of a procedure execution with its condition applications. `plate_tag`
    is the output plate the well is on (None: the primary output plate)."""
    position : str
    plate_tag : Optional[str] = None
    condition_application_tags : List[str] = Field(default_factory=list)



class ExecutionWellMetricModel(BaseModel):
    """A measured value of a single well: the trait defines the measured quantity (e.g. u g/uL of
    the concentration attribute). `plate_tag` is the plate the well is on (None: the primary plate
    of that side)."""
    position : str
    plate_tag : Optional[str] = None
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
    input_plate_tag : Optional[str] = None
    output_plate_tag : Optional[str] = None
    """A draft setup can be saved at any stage: as long as no wells and no metrics are given, the
    plates may be omitted (a partial save of the work done so far)."""
    responsible_user_tag : Optional[str] = None
    additional_input_plate_tags : List[str] = Field(default_factory=list)
    additional_output_plate_tags : List[str] = Field(default_factory=list)
    """Further input / output plates of the execution: a design can hold several plates per side when
    the samples (or the produced wells) do not fit on a single plate (e.g. >96 samples). The primary
    tags above stay first in the effective plate lists; well positions are unique per plate, so wells
    on the additional plates must carry `plate_tag` and transfer targets there are plate-qualified
    ("plate_tag:A1")."""
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
    block_output_wells : Optional[bool] = None
    """Overrides whether the output wells stay blocked after this change (e.g. an aborted robot run
    with dirty wells must stay blocked); omitted it defaults to the outcome (SUCCEEDED blocks,
    FAILED/ABORTED release the wells for a re-run)."""



class ProcedureExecutionInputWellModel(BaseModel):
    """A stored input well of a procedure execution. `plate_tag` is the input plate the well is on
    (for single-plate executions it equals the primary input plate)."""
    position : str
    plate_tag : Optional[str] = None
    row_index : int
    column_index : int
    sample_tags : List[str] = Field(default_factory=list)
    output_positions : List[str] = Field(default_factory=list)
    """Plate-qualified where needed: plain positions refer to the primary output plate, wells on the
    additional output plates are referenced as "plate_tag:A1"."""
    metrics : List[ProcedureExecutionWellMetricModel] = Field(default_factory=list)



class ProcedureExecutionOutputWellModel(BaseModel):
    """A stored output well of a procedure execution. The sample tags are derived from the transfer
    map (pooling and splitting supported). `plate_tag` is the output plate the well is on."""
    position : str
    plate_tag : Optional[str] = None
    row_index : int
    column_index : int
    sample_tags : List[str] = Field(default_factory=list)
    condition_application_tags : List[str] = Field(default_factory=list)
    metrics : List[ProcedureExecutionWellMetricModel] = Field(default_factory=list)



def _none_to_list(value):
    """Pydantic model hook: a null list (e.g. from a property that does not exist yet on a fresh
    draft execution) is treated as an empty list instead of a validation error."""
    return [] if value is None else value


class ProcedureExecutionModel(BaseModel):
    """A concrete execution of a published modular procedure on a set of samples, mapping input
    plate wells to output plate wells. Executions start as DRAFT (backend-generated ID, setup can
    be saved and continued later, nothing is blocked yet); starting runs the full validation and
    moves them to RUNNING. The plates are optional only while an execution is still an empty draft."""
    tag : str
    procedure_tag : str
    input_plate_tags : List[str] = Field(default_factory=list)
    output_plate_tags : List[str] = Field(default_factory=list)
    """All input / output plates of the execution (multi-plate support for large sample numbers);
    the compat single tags below are the primary (first) plates of each side."""
    input_plate_tag : Optional[str] = None
    output_plate_tag : Optional[str] = None
    user_tag : str
    responsible_user_tag : Optional[str] = None
    created_at : Optional[float] = None
    status : ProcedureExecutionStatusEnum = Field(default=ProcedureExecutionStatusEnum.RUNNING)
    wells_blocked : bool = True
    """Whether the output wells of this execution block re-use: true while running; on confirmation it
    follows the outcome unless the confirming user chose otherwise."""
    finished_at : Optional[float] = None
    finished_by : Optional[str] = None
    finish_comment : Optional[str] = None
    done_submission_tags : List[str] = Field(default_factory=list)
    input_well_metrics : List[ProcedureExecutionWellMetricModel] = Field(default_factory=list)
    _coerce_none_lists = field_validator("done_submission_tags", "input_well_metrics",
                                         "input_plate_tags", "output_plate_tags", mode="before")(_none_to_list)
    input_wells : List[ProcedureExecutionInputWellModel] = Field(default_factory=list)
    output_wells : List[ProcedureExecutionOutputWellModel] = Field(default_factory=list)

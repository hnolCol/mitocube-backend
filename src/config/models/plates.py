from pydantic import BaseModel, Field
from typing import List, Optional


class PlateInsertModel(BaseModel):
    """
    What the user fills in when creating a plate. The traits are not fixed: any attribute of the
    storage attribute group (including attributes added later by the admins) can be selected.

    Parameter
    ---------
    name : str
        Label of the physical plate, e.g. 'P-96-001'. Must be unique.
    trait_tags : dict
        Maps the tag of an attribute of the storage attribute group to the tag of the trait selected
        for it, e.g. {'att_container_format': 'att_container_format:8x12'}. Exactly one of the selected
        traits must have a value of the form '<rows>x<columns>' (e.g. 8x12) - it defines the container
        format, the number of wells and the plate name prefix.
    location : str, optional
        Free text, e.g. 'Rack 3, Shelf 2'.
    description : str, optional
        Free text.
    """
    name : str = Field(..., min_length=1, max_length=50)
    trait_tags : dict = Field(default_factory=dict)
    location : Optional[str] = None
    description : Optional[str] = None

class PlateApplicationModel(BaseModel):
    "A trait selected for a plate, resolved via its condition application, e.g. container format -> 96-well plate."
    attribute_tag : str
    attribute_text : str
    trait_tag : str
    trait_text : str

class PlateModel(BaseModel):
    "A plate as stored in the database. Its selected attributes come from its condition applications."
    tag : str
    name : str
    rows : int
    columns : int
    n_wells : Optional[int] = None
    location : Optional[str] = None
    description : Optional[str] = None
    created_at : float
    user_tag : Optional[str] = None
    created_by : Optional[str] = None
    n_used_wells : int = 0
    n_runlists : int = 0
    n_submissions : int = 0
    format : Optional[str] = None
    applications : List[PlateApplicationModel] = []


class PlateOptionModel(BaseModel):
    "A selectable trait in the create plate dialog."
    tag : str
    text : str
    description : Optional[str] = None
    rows : Optional[int] = None      # only for traits with a '<rows>x<columns>' value
    columns : Optional[int] = None   # only for traits with a '<rows>x<columns>' value

class PlateAttributeOptionsModel(BaseModel):
    """
    An attribute of the storage attribute group with its selectable traits. Attributes can be
    nested: an attribute with a parent_tag (e.g. a container material under the container format)
    is offered when its parent attribute has a selected trait.
    """
    tag : str
    text : str
    description : Optional[str] = None
    parent_tag : Optional[str] = None
    is_format : bool = False
    traits : List[PlateOptionModel] = []


class PlateRunlistModel(BaseModel):
    "A runlist that has at least one run on a plate, with the per-plate usage."
    runlist_tag : str
    created_at : float
    instrument_tag : Optional[str] = None
    instrument_text : Optional[str] = None
    fractionated : bool = False
    scrambled : bool = False
    n_runs_on_plate : int
    used_positions : list[str] = []
    user_tag : Optional[str] = None
    user_firstname : Optional[str] = None
    user_lastname : Optional[str] = None
    submission_tag : str
    submission_label : str
    submission_title : Optional[str] = None


class PlateSubmissionModel(BaseModel):
    "A submission that was measured (via any runlist) on a plate."
    submission_tag : str
    submission_label : str
    submission_title : Optional[str] = None
    user_tag : Optional[str] = None
    user_firstname : Optional[str] = None
    user_lastname : Optional[str] = None
    n_runs_on_plate : int = 0
    n_runlists : int = 0


class PlateWellSubmissionModel(BaseModel):
    "A single well of a plate, empty wells have submission_tag None."
    row_index : int
    column_index : int
    position : str
    submission_tag : Optional[str] = None
    runlist_tag : Optional[str] = None
    run_name : Optional[str] = None
    measured_at : Optional[float] = None


class PlateSubmissionLegendModel(BaseModel):
    "Legend entry for one distinct submission measured on a plate."
    submission_tag : str
    submission_label : str
    submission_title : Optional[str] = None
    user_tag : Optional[str] = None
    user_firstname : Optional[str] = None
    user_lastname : Optional[str] = None
    n_wells : int


class PlateSubmissionsLayoutModel(BaseModel):
    "Full well grid of a plate with the well -> submission mapping and the submission legend."
    plate_tag : str
    rows : int
    columns : int
    wells : list[PlateWellSubmissionModel] = []
    submissions : list[PlateSubmissionLegendModel] = []


class PlateOptionsModel(BaseModel):
    "All attributes of the storage attribute group with their selectable traits."
    attributes : List[PlateAttributeOptionsModel] = []

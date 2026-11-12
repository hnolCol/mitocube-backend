from pydantic import BaseModel, Field
from typing import Optional


class PlateInsertModel(BaseModel):
    """
    What the user fills in when creating a plate.

    Parameter
    ---------
    name : str
        Label of the physical plate, e.g. 'P-96-001'. Must be unique.
    format_trait_tag : str
        Trait of the plate format attribute (value e.g. '8x12'). Rows and columns are taken from it.
    cold_storage_trait_tag : str, optional
        Trait of the cold storage attribute (e.g. -80 °C freezer).
    plate_type_trait_tag : str, optional
        Trait of the plate type attribute (e.g. PCR plate (skirted)).
    vendor_trait_tag : str, optional
        Trait of the vendor attribute (e.g. Eppendorf).
    location : str, optional
        Free text, e.g. 'Rack 3, Shelf 2'.
    description : str, optional
        Free text.
    """
    name : str = Field(..., min_length=1, max_length=50)
    format_trait_tag : str
    cold_storage_trait_tag : Optional[str] = None
    plate_type_trait_tag : Optional[str] = None
    vendor_trait_tag : Optional[str] = None
    location : Optional[str] = None
    description : Optional[str] = None


class PlateModel(BaseModel):
    "A plate as stored in the database. Format, storage, type and vendor come from its condition applications."
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
    cold_storage : Optional[str] = None
    plate_type : Optional[str] = None
    vendor : Optional[str] = None


class PlateOptionModel(BaseModel):
    "A selectable trait in the create plate dialog."
    tag : str
    text : str
    description : Optional[str] = None
    rows : Optional[int] = None      # only for formats
    columns : Optional[int] = None   # only for formats


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
    formats : list[PlateOptionModel] = []
    cold_storage : list[PlateOptionModel] = []
    plate_type : list[PlateOptionModel] = []
    vendor : list[PlateOptionModel] = []
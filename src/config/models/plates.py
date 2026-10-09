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


class PlateOptionsModel(BaseModel):
    formats : list[PlateOptionModel] = []
    cold_storage : list[PlateOptionModel] = []
    plate_type : list[PlateOptionModel] = []
    vendor : list[PlateOptionModel] = []
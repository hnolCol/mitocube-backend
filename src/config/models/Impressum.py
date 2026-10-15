from pydantic import BaseModel
from typing import Optional

IMPRESSUM_TAG = "mitocube_impressum"


class ImpressumModel(BaseModel):
    tag : str = IMPRESSUM_TAG
    title : Optional[str] = None
    text : str = ""
    created_at : Optional[float] = None
    updated_at : Optional[float] = None
    updated_by : Optional[str] = None


class ImpressumUpdateModel(BaseModel):
    title : Optional[str] = None
    text : str

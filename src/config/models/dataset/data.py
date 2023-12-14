from pydantic import BaseModel
from pydantic import Field
from pydantic import field_serializer 
from typing import List, Dict, Any

import pandas as pd 

from config.settings.db import get_db_settings


class DatasetPCAResponse(BaseModel):
    """Dataset Repsonse model for a PCA"""
    projection : List[Dict]
    drivers : List[Dict]
    variance_explained : List[float]
    samples_attributes : Dict[str,List[str]]

    
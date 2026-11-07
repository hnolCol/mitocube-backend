from typing import List

from pydantic import BaseModel


class ProjectionPointModel(BaseModel):
    sample_tag: str
    submission_tag: str
    components: List[float]


class ProjectionDriverModel(BaseModel):
    tag: str
    components: List[float]


class ProteomeProjectionResponseModel(BaseModel):
    proteome_tag: str
    method: str
    n_components: int
    variance_explained: List[float]
    n_proteins: int
    n_submissions: int
    submission_tags: List[str]
    points: List[ProjectionPointModel]
    drivers: List[ProjectionDriverModel]

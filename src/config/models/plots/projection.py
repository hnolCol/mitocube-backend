from typing import List

from pydantic import BaseModel


class ProjectionPointModel(BaseModel):
    sample_tag: str
    submission_tag: str
    components: List[float]
    condition_applications: List[str] = []


class ProjectionDriverModel(BaseModel):
    tag: str
    components: List[float]


class ConditionCentroidModel(BaseModel):
    condition_application_tag: str
    count: int
    components: List[float]


class ConditionAssociationModel(BaseModel):
    condition_application_tag: str
    mean_z: float
    n_samples: int


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
    condition_centroids: List[ConditionCentroidModel] = []


class ProteinAttributeEffectModel(BaseModel):
    attribute_tag: str
    ca_tag: str
    effect: float
    mean_z_in: float
    mean_z_out: float
    n_in: int
    n_out: int


class ProteomeProjectionDriverResponseModel(BaseModel):
    proteome_tag: str
    protein_tag: str
    n_components: int
    variance_explained: List[float]
    n_submissions: int
    submission_tags: List[str]
    driver: ProjectionDriverModel
    condition_associations: List[ConditionAssociationModel] = []
    attribute_effects: List[ProteinAttributeEffectModel] = []


class ProteinEffectModel(BaseModel):
    tag: str
    effect: float
    mean_z_in: float
    mean_z_out: float
    n_in: int
    n_out: int
    cohens_d: float | None


class ProteomeProjectionEffectResponseModel(BaseModel):
    proteome_tag: str
    ca_tag: str
    n_submissions: int
    submission_tags: List[str]
    n_proteins: int
    effects: List[ProteinEffectModel]


class AttributeConditionEffectModel(BaseModel):
    ca_tag: str
    n_in: int
    n_out: int
    separation: float
    effects: List[ProteinEffectModel]


class AttributeProteinConditionModel(BaseModel):
    ca_tag: str
    mean_z: float
    n_samples: int
    n_submissions: int


class AttributeProteinEffectModel(BaseModel):
    tag: str
    rank: int
    effect: float
    max_abs_ca_effect: float
    conditions: List[AttributeProteinConditionModel] = []


class ProteomeAttributeProteinEffectsResponseModel(BaseModel):
    attribute_tag: str
    n_submissions: int
    ca_tags: List[str]
    proteins: List[AttributeProteinEffectModel]


class ProteomeProjectionAttributeEffectResponseModel(BaseModel):
    proteome_tag: str
    attribute_tag: str
    n_components: int
    variance_explained: List[float]
    n_submissions: int
    submission_tags: List[str]
    conditions: List[AttributeConditionEffectModel]

from pydantic import BaseModel
from typing import Optional, List
from config.models.attributes import AttributeTree
from config.models.genotype import InsertGeneticApplicationModel

class PhenotypeAssociationModel(BaseModel):
    tag: str
    description: Optional[str] = None
    observation_notes: Optional[str] = None
    att_protein_mutation: Optional[str] = None
    publication: Optional[str] = None
    phenotype_tag: Optional[str] = None
    disease_tag: Optional[str] = None
    protein_tag: Optional[str] = None
    variant_tag: Optional[str] = None
    genotype_tag: Optional[str] = None
    created_at: Optional[float] = None

class PhenotypeAssociationInputModel(BaseModel):
    description: Optional[str] = None
    observation_notes: Optional[str] = None
    att_protein_mutation: Optional[str] = None
    publication: Optional[str] = None
    phenotype_tag: str
    protein_tag: Optional[str] = None
    disease_tag: Optional[str] = None
    variant_tag: Optional[str] = None
    genotype_tag: Optional[str] = None
    genotype: Optional[InsertGeneticApplicationModel] = None
    condition_applications: Optional[List[AttributeTree]] = None

class PhenotypeAssociationFullInsertModel(BaseModel):
    description: Optional[str] = None
    observation_notes: Optional[str] = None
    att_protein_mutation: Optional[str] = None
    publication: Optional[str] = None
    phenotype_tag: str
    protein_tag: Optional[str] = None
    genotype_tag: Optional[str] = None         
    genotype: Optional[InsertGeneticApplicationModel] = None  
    condition_applications: Optional[List[AttributeTree]] = None
    disease_tag: Optional[str] = None
    disease_text: Optional[str] = None
    variant_tag: Optional[str] = None
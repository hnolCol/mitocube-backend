from fastapi import APIRouter, Depends, HTTPException
from typing import List
from config.models.PhenotypeAssociation import (
    PhenotypeAssociationModel,
    PhenotypeAssociationInputModel,
    PhenotypeAssociationFullInsertModel,
)
from config.models.diseases import DiseaseInputModel
from config.models.user import UserModel
from services.users import get_user_from_token, is_user_admin
from services.random_generators import get_random_string
from lib.database.Database import Database

DB = Database.DB()
router = APIRouter(prefix="/api/phenotype_associations", tags=["PhenotypeAssociations"])
not_found = HTTPException(status_code=404, detail="PhenotypeAssociation not found.")


@router.get("")
def find_phenotype_associations(
    query: str = "",
    phenotype_tag: str = None,
    disease_tag: str = None,
    protein_tag: str = None,
    genotype_tag: str = None,
    limit: int = 20,
    user: UserModel = Depends(get_user_from_token)
) -> List[str]:
    "Find phenotype associations with optional filters."
    if phenotype_tag:
        return DB.phenotype_associations.find_by_phenotype(phenotype_tag=phenotype_tag, limit=limit)
    if disease_tag:
        return DB.phenotype_associations.find_by_disease(disease_tag=disease_tag, limit=limit)
    if protein_tag:
        return DB.phenotype_associations.find_by_protein(protein_tag=protein_tag, limit=limit)
    if genotype_tag:
        return DB.phenotype_associations.find_by_genotype(genotype_tag=genotype_tag, limit=limit)
    return DB.phenotype_associations.find(query=query, limit=limit)


@router.get("/{tag}")
def get_phenotype_association(
    tag: str,
    user: UserModel = Depends(get_user_from_token)
) -> PhenotypeAssociationModel:
    "Returns a phenotype association by its unique tag."
    if not DB.phenotype_associations.exists(tag):
        raise not_found
    return DB.phenotype_associations.get(tag)


@router.post("")
def insert_phenotype_association(
    data: PhenotypeAssociationFullInsertModel,
    user: UserModel = Depends(get_user_from_token)
) -> str:
    disease_tag = data.disease_tag

    if disease_tag and not DB.diseases.exists(disease_tag):
        # ClinVar disease
        DB.diseases.insert(
            DiseaseInputModel(tag=disease_tag, text=data.disease_text or disease_tag),
            user_tag=user.tag
        )
    elif not disease_tag and data.disease_text:
        # free text disease
        disease_tag = get_random_string(8)
        DB.diseases.insert(
            DiseaseInputModel(tag=disease_tag, text=data.disease_text),
            user_tag=user.tag
        )

    association = PhenotypeAssociationInputModel(
        description=data.description,
        observation_notes=data.observation_notes,
        att_protein_mutation=data.att_protein_mutation,
        publication=data.publication,
        phenotype_tag=data.phenotype_tag,
        protein_tag=data.protein_tag,
        disease_tag=disease_tag,
        variant_tag=data.variant_tag,
        genotype_tag=data.genotype_tag,
        genotype=data.genotype, 
        condition_applications=data.condition_applications,
    )
    return DB.phenotype_associations.insert(association, user_tag=user.tag)


@router.delete("/{tag}")
def delete_phenotype_association(
    tag: str,
    user: UserModel = Depends(is_user_admin)
) -> bool:
    "Soft delete a phenotype association."
    if not DB.phenotype_associations.exists(tag):
        raise not_found
    return DB.phenotype_associations.delete(tag)
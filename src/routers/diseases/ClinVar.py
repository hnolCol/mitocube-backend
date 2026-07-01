from fastapi import APIRouter, Depends, HTTPException
from config.models.user import UserModel
from services.users import get_user_from_token
from services.ClinVar import search_clinvar, lookup_variant_by_mutation, search_diseases_clinvar, clinvar_variant_to_genotype_components

router = APIRouter(prefix="/api/clinvar", tags=["ClinVar"])


@router.get("/search")
def search_clinvar_by_disease(
    disease: str,
    limit: int = 20,
    user: UserModel = Depends(get_user_from_token)
):
    "Search ClinVar by disease name. Returns variants and diseases."
    try:
        variants, diseases = search_clinvar(disease=disease, limit=limit)
        return {"variants": variants, "diseases": diseases}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/variant_lookup")
def lookup_variant(
    gene: str,
    mutation: str,
    limit: int = 10,
    user: UserModel = Depends(get_user_from_token)
):
    "Free-text mutation + gene symbol -> candidate ClinVar variants for user to pick from."
    try:
        variants = lookup_variant_by_mutation(gene, mutation, limit)
        return {"variants": variants, "found": len(variants) > 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/disease_search")
def search_diseases(
    query: str,
    limit: int = 20,
    user: UserModel = Depends(get_user_from_token)
):
    "Search ClinVar disease database by name for the disease picker."
    try:
        diseases = search_diseases_clinvar(query, limit)
        return {"diseases": diseases}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@router.get("/variant_to_genotype")
def variant_to_genotype(
    variant_id: str,
    protein_tag: str,
    proteome_tag: str,
    user: UserModel = Depends(get_user_from_token),
):
    """
    Given a ClinVar variant ID + protein context, return a ready-to-POST
    InsertGeneticApplicationModel template (components only — text/description
    left for the frontend to fill in before POSTing to /api/genotypes).
    """
    try:
        # re-fetch the variant summary by its ID
        from services.ClinVar import fetch_summaries
        variants, _ = fetch_summaries([variant_id])
        if not variants:
            raise HTTPException(status_code=404, detail="Variant not found in ClinVar.")
        variant = variants[0]

        components = clinvar_variant_to_genotype_components(variant, protein_tag, proteome_tag)

        return {
            "text": variant.title,
            "description": variant.clinical_significance or "",
            "publication": None,
            "technical_text": None,
            "components": components,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
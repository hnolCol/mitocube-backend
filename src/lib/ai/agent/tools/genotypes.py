from typing import List, Dict, Any, Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from lib.database.Database import Database
from services.random_generators import get_random_string

DB = Database.DB()


# ============================================================
# Helper
# ============================================================

def transform_tree(item, ca_id: str) -> Dict[str, Any]:
    return {
        "type": "attribute",
        "id": ca_id,
        "tag": item.attribute_tag,
        "children": [
            {
                "type": "trait",
                "tag": item.trait_tag,
                "value": item.value,
                "id": ca_id,
                "children": [
                    transform_tree(child, ca_id=ca_id)
                    for child in item.children
                ]
            }
        ]
    }


# ============================================================
# Input Schemas
# ============================================================

class GenotypeTagInput(BaseModel):
    genotype_tag: str = Field(
        ...,
        description="Genotype identifier"
    )


class FindGenotypesInput(BaseModel):
    search_string: Optional[str] = Field(
        None,
        description="Search text for genotype search"
    )

    user_tag: Optional[str] = Field(
        None,
        description="Only return genotypes created by this user"
    )

    limit: Optional[int] = Field(
        50,
        description="Maximum number of genotype tags returned"
    )


class GetGenotypesInput(BaseModel):
    proteome_tags: Optional[List[str]] = Field(
        None,
        description="Filter genotypes by proteome tags"
    )

    protein_tags: Optional[List[str]] = Field(
        None,
        description="Filter genotypes by affected protein tags"
    )


# ============================================================
# Search Tools
# ============================================================

@tool("find_genotypes", args_schema=FindGenotypesInput)
def find_genotypes(
    search_string: str = None,
    user_tag: str = None,
    limit: int = 50
) -> List[str]:
    """
    Search genotypes by free text search and return matching genotype tags.
    """
    return DB.genotypes.find(
        search_string=search_string,
        user_tag=user_tag,
        limit=limit
    )


@tool("check_genotype_exists", args_schema=GenotypeTagInput)
def check_genotype_exists(genotype_tag: str) -> bool:
    """
    Check whether a genotype exists.
    """
    return DB.genotypes.exists(tag=genotype_tag)


# ============================================================
# Genotype Metadata
# ============================================================

@tool("get_genotype_item", args_schema=GenotypeTagInput)
def get_genotype_item(genotype_tag: str):
    """
    Retrieve the complete genotype object.
    """
    if not DB.genotypes.exists(tag=genotype_tag):
        return None

    return DB.genotypes.get_item(tag=genotype_tag)


@tool("get_genotype_description", args_schema=GenotypeTagInput)
def get_genotype_description(genotype_tag: str) -> Optional[str]:
    """
    Retrieve the genotype description.
    """
    if not DB.genotypes.exists(tag=genotype_tag):
        return None

    return DB.genotypes.get_description(tag=genotype_tag)


@tool("get_genotype_text", args_schema=GenotypeTagInput)
def get_genotype_text(genotype_tag: str) -> Optional[str]:
    """
    Retrieve the full genotype text representation.
    """
    if not DB.genotypes.exists(tag=genotype_tag):
        return None

    return DB.genotypes.get_text(tag=genotype_tag)


@tool("get_genotype_creator", args_schema=GenotypeTagInput)
def get_genotype_creator(genotype_tag: str) -> Optional[str]:
    """
    Retrieve the creator user tag of a genotype.
    """
    if not DB.genotypes.exists(tag=genotype_tag):
        return None

    return DB.genotypes.get_creator(tag=genotype_tag)


# ============================================================
# Proteome / Protein Tools
# ============================================================

@tool("get_genotype_proteome", args_schema=GenotypeTagInput)
def get_genotype_proteome(genotype_tag: str) -> Optional[str]:
    """
    Retrieve the proteome associated with a genotype.
    """
    if not DB.genotypes.exists(tag=genotype_tag):
        return None

    return DB.genotypes.get_proteome(tag=genotype_tag)


@tool("get_genotype_proteins", args_schema=GenotypeTagInput)
def get_genotype_proteins(genotype_tag: str) -> List[str]:
    """
    Retrieve protein tags associated with a genotype.
    """
    if not DB.genotypes.exists(tag=genotype_tag):
        return []

    return DB.genotypes.get_proteins(tag=genotype_tag)


@tool("get_genotypes", args_schema=GetGenotypesInput)
def get_genotypes(
    proteome_tags: Optional[List[str]] = None,
    protein_tags: Optional[List[str]] = None,
):
    """
    Retrieve genotypes filtered by proteome tags or protein tags.
    """
    return DB.genotypes.get(
        proteome_tags=proteome_tags,
        protein_tags=protein_tags,
    )


# ============================================================
# Usage / Statistics
# ============================================================

@tool("get_genotype_relationship_count", args_schema=GenotypeTagInput)
def get_genotype_relationship_count(genotype_tag: str) -> int:
    """
    Count how many samples reference a genotype.
    """
    if not DB.genotypes.exists(tag=genotype_tag):
        return 0

    return DB.samples.count(genotype_tag=genotype_tag)


# ============================================================
# Condition Applications
# ============================================================

@tool("get_genotype_condition_applications", args_schema=GenotypeTagInput)
def get_genotype_condition_applications(
    genotype_tag: str
) -> List[str]:
    """
    Retrieve condition application tags associated with a genotype.
    """
    if not DB.genotypes.exists(tag=genotype_tag):
        return []

    return DB.genotypes.get_condition_applications(
        tag=genotype_tag
    )


@tool("get_genotype_condition_application_data", args_schema=GenotypeTagInput)
def get_genotype_condition_application_data(
    genotype_tag: str
):
    """
    Retrieve detailed condition application data associated with a genotype.
    """
    if not DB.genotypes.exists(tag=genotype_tag):
        return None

    return DB.genotypes.get_condition_application_data(
        tag=genotype_tag
    )


@tool("get_genotype_condition_application_tree", args_schema=GenotypeTagInput)
def get_genotype_condition_application_tree(
    genotype_tag: str
) -> List[Dict[str, Any]]:
    """
    Retrieve the condition application tree structure for a genotype.
    """
    if not DB.genotypes.exists(tag=genotype_tag):
        return []

    ca_tags = DB.genotypes.get_condition_applications(
        tag=genotype_tag
    )

    result = []

    for ca_tag in ca_tags:
        tree = DB.condition_applications.get_tree(
            tag=ca_tag
        )

        if tree:
            result.append(
                transform_tree(
                    tree[0],
                    ca_id=get_random_string(4)
                )
            )

    return result


# ============================================================
# Registry
# ============================================================

GENOTYPE_TOOLS = [
    find_genotypes,
    check_genotype_exists,
    get_genotype_item,
    get_genotype_description,
    get_genotype_text,
    get_genotype_creator,
    get_genotype_proteome,
    get_genotype_proteins,
    get_genotypes,
    get_genotype_relationship_count,
    get_genotype_condition_applications,
    get_genotype_condition_application_data,
    get_genotype_condition_application_tree,
]
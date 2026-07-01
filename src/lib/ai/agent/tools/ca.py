from typing import List, Dict, Any, Optional, Union
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from lib.database.Database import Database
from config.models.attributes import AttributeTree
from config.models.conditions_applications import (
    ConditionApplicationAttributeModel,
    ConditionApplicationStateModel,
)

from config.models.parameter import APIParamString

DB = Database.DB()

# ----------------------------
# Input Schemas
# ----------------------------

class SubmissionTagInput(BaseModel):
    submission_tag: str = Field(..., description="Submission identifier")

class SubmissionAttributesInput(BaseModel):
    submission_tag: str = Field(..., description="Submission identifier")
    include_genotypes: bool = Field(True, description="Include genotype attribute if available")

class SampleCAInput(BaseModel):
    submission_tag: str = Field(..., description="Submission identifier")
    attribute_tags: Optional[List[str]] = Field(
        None,
        description="Filter by attribute tags"
    )
    return_unique: bool = Field(
        False,
        description="Return only unique condition applications across samples"
    )
    include_genotype: bool = Field(
        True,
        description="Include genotype information if available"
    )

class SampleCAAttributesInput(BaseModel):
    submission_tag: str = Field(..., description="Submission identifier")
    include_genotypes: bool = Field(True, description="Include genotype attribute if available")

class CATreeInput(BaseModel):
    submission_tag: str = Field(..., description="Submission identifier")

class UpdateCAInput(BaseModel):
    submission_tag: str = Field(..., description="Submission identifier")
    selected_traits: List[Dict[str, Any]] = Field(
        ...,
        description="AttributeTree-like structures for updating condition applications"
    )


# ----------------------------
# Tools
# ----------------------------

@tool("get_submission_condition_applications", args_schema=SubmissionTagInput)
def get_submission_condition_applications(submission_tag: str) -> List[Any]:
    """
    Get condition applications for a submission.
    """
    return DB.submissions.get_conditions_applications(submission_tag)


@tool("get_submission_condition_application_attributes", args_schema=SubmissionAttributesInput)
def get_submission_condition_application_attributes(
    submission_tag: str,
    include_genotypes: bool = True
) -> List[str]:
    """
    Get all condition application attribute tags for a submission.
    """
    ca_tags = DB.submissions.get_conditions_applications(submission_tag, group_by_attribute=False)

    attribute_tags = [
        DB.condition_applications.get_attribute(ca_tag)
        for ca_tag in ca_tags
    ]

    if include_genotypes and DB.submissions.has_genotypes(tag=submission_tag):
        attribute_tags = ["att_genotype"] + attribute_tags

    return [a for a in attribute_tags if a is not None]


@tool("get_submission_sample_condition_applications", args_schema=SampleCAInput)
def get_submission_sample_condition_applications(
    submission_tag: str,
    attribute_tags: Optional[List[str]] = None,
    return_unique: bool = False,
    include_genotype: bool = True
) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Get condition applications for samples in a submission.
    """

    sample_tags = DB.submissions.get_samples(tag=submission_tag)
    genotype_exists = DB.submissions.has_genotypes(tag=submission_tag)

    rows = []

    for sample_tag in sample_tags:
        row = {"tag": sample_tag}

        ca_groups = DB.samples.get_condition_applications(
            tag=sample_tag,
            attribute_tags=APIParamString(param=attribute_tags).param,
            group_by_attribute=True
        )

        if genotype_exists and include_genotype:
            row["att_genotype"] = DB.samples.get_sample_genotype(tag=sample_tag)

        for ca in ca_groups:
            row[ca.attribute_tag] = ca.condition_application_tags

        rows.append(row)

    if not return_unique:
        return rows

    # ---- unique aggregation ----
    unique = {}
    for row in rows:
        for k, v in row.items():
            if k == "tag":
                continue
            unique.setdefault(k, set())
            if isinstance(v, list):
                unique[k].update([";".join(v)])
            else:
                unique[k].add(str(v))

    return {
        k: [x.split(";") for x in list(v)]
        for k, v in unique.items()
    }


@tool("get_submission_sample_condition_application_attributes", args_schema=SampleCAAttributesInput)
def get_submission_sample_condition_application_attributes(
    submission_tag: str,
    include_genotypes: bool = True
) -> List[str]:
    """
    Get condition application attributes for samples of a submission.
    """
    if not DB.submissions.exists(tag=submission_tag):
        return []

    sample_tags = DB.submissions.get_samples(tag=submission_tag)

    if not sample_tags:
        return []

    attribute_tags = []

    for sample_tag in sample_tags:
        ca_tags = DB.samples.get_condition_applications(
            tag=sample_tag,
            group_by_attribute=False
        )
        attribute_tags.extend([
            DB.condition_applications.get_attribute(ca_tag)
            for ca_tag in ca_tags
        ])

    if include_genotypes and DB.submissions.has_genotypes(tag=submission_tag):
        attribute_tags.append("att_genotype")

    return list(set([a for a in attribute_tags if a is not None]))


@tool("get_ca_tree_for_submission", args_schema=CATreeInput)
def get_ca_tree_for_submission(submission_tag: str) -> List[Dict[str, Any]]:
    """
    Get condition application tree for a submission.
    """
    if not DB.submissions.exists(tag=submission_tag):
        return []

    ca_tags = DB.submissions.get_conditions_applications(tag=submission_tag)

    result = []

    for ca_tag in ca_tags:
        tree = DB.condition_applications.get_tree(tag=ca_tag)
        if tree:
            result.append({
                "submission_tag": submission_tag,
                "tree": transform_tree(tree[0], ca_id=ca_tag)
            })

    return result


# ----------------------------
# Helper (fixed version)
# ----------------------------

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


# ----------------------------
# Tool registry
# ----------------------------

CONDITION_APPLICATION_TOOLS = [
    get_submission_condition_applications,
    get_submission_condition_application_attributes,
    get_submission_sample_condition_applications,
    get_submission_sample_condition_application_attributes,
    get_ca_tree_for_submission,
]

from typing import List, Tuple

from langchain_core.tools import tool
from pydantic import BaseModel, Field
from lib.database.Database import Database 
from config.models.submissions.states import SubmissionStatesEnums
DB = Database.DB()

class FindProteinsInput(BaseModel):
    search_string : str = Field(None, description="Search string to match against gene names and protein tags.")
    annotation_tags : List[str] = Field(None, description="Filter proteins by annotation tags. An annotation tag corresponds to a group of proteins that are annotated with a specific feature, such as membership in MitoCarta3.0 or a specific GO term.")
    submission_tag : str = Field(None, description="Filter proteins that are quantified in a specific submission.")
    limit : int = Field(None, description="Limit the number of proteins returned.")

class ProteinTagInput(BaseModel):
    protein_tags: List[str] = Field(..., description="Exact protein tags (uniprot accessions) to retrieve information for")


@tool("find_proteins", args_schema=FindProteinsInput)
def find_proteins(search_string : str = None, annotation_tags : List[str] = None, submission_tag : str = None, limit : int = None) -> Tuple[List[str],int]:
    """
    Returns the protein tags matching the criteria, and returns the count of matching proteins. The protein tag corresponds to the uniprot accession. 
    Search for proteins by name (e.g. gene name) or annotation (Annotations are group of proteins that are grouped into Annotation Groups - available to get in other tools).
    You can also filter by submission tag and annotation tag - hence it will only provide proteins that are quantified in the submission or part of the annotation_tag.
    If you provide a search_string, it will be matched against gene names and protein tags. 
    """
    if submission_tag is not None and not DB.submissions.exists(tag = submission_tag): raise ValueError(f"Submission tag {submission_tag} does not exist.")

    tags = DB.protein_groups.find(search_string=search_string, annotation_tags=annotation_tags, submission_tag=submission_tag, limit = limit)
    return tags, len(tags)

@tool("get_protein_gene_name", args_schema=ProteinTagInput)
def get_protein_gene_name(protein_tags: List[str]) -> List[Tuple[str,str]]:
    """
    Given a list of protein tags (uniprot accessions), return their corresponding gene names. 
    If a protein tag does not exist, it will be ignored and not included in the output.
    """
    results = []
    for tag in protein_tags:
        if DB.proteins.exists(tag = tag):
            gene_name = DB.proteins.get_gene_name(tag = tag)
            results.append((tag, gene_name))
    return results
   
PROTEIN_TOOLS = [find_proteins, get_protein_gene_name]
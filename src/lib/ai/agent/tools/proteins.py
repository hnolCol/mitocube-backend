
from typing import List, Literal, Tuple
import pandas as pd
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
   
@tool("get_protein_abundance_in_submissions")
def get_protein_abundance_in_submissions(protein_tag : str, submission_tag: str, metrics : Literal["raw","z_score_sample","z_score_protein_group","log2_fc_vs_mean"] = "log2_fc_vs_mean") -> Tuple[str, pd.DataFrame, pd.DataFrame]:
    """
    Returns the abundance of a protein in a specific submission given the sample_tag, the condition (ConditionApplication, or ca_tag) and the protein_tag. 
    The ca tags are the condition applications that describe the samples in the submission. Each ca_tag corresponds to a specific combination. A single sample 
    can be connected to multiple condition applications, and a single condition application can be connected to multiple samples.
    The metric describe what kind of quantification value is returned. Raw is the log2 LFQ intensity, z_score_sample is the z-score of the protein in the sample, z_score_protein_group is the z-score of the protein across all samples in the submission, and log2_fc_vs_mean is the log2 fold change of the protein in the sample compared to the mean of all samples in the submission.
   
    The output is a Tuple of the
    0 - protein_tag (uniprot accession)
    1 - DataFrame with the abundance values for each sample in the submission. The index is the sample_tag, and the columns are the abundance values for each metric. 
    2 - DataFrame with the condition application attributes for each sample in the submission. The index is the sample_tag, and the columns are the condition application attribute_tags, the cell values are the ca_tags that describe the sample. If a sample is connected to multiple condition applications, the cell will contain a list of ca_tags.
    The ca_tags can be used to retireve the text describing them with the ca_tools
    
    """ 
    if not DB.proteins.exists(tag = protein_tag): raise ValueError(f"Protein tag {protein_tag} does not exist.") 
    ca_tags = DB.samples.get_sample_condition_application_map_for_submission(submission_tag=submission_tag) #returns a dataframe, sample_tag as index. Attribute tag as columns and ca_tags for each sample_tag.
    data = DB.features.get_quantification_per_sample(tag = protein_tag, submission_tags = [submission_tag]) 
  
    return protein_tag, data, ca_tags

PROTEIN_TOOLS = [find_proteins, get_protein_gene_name, get_protein_abundance_in_submissions]
from pydantic import BaseModel

class Feature(BaseModel):
    """Base Model for a Feature"""
    uniprot_id : str 
    gene_name : str 
    protein_name : str 
    organism : str
    length : int 

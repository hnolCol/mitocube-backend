from pydantic import BaseModel, field_validator


from typing import Optional, Union, List, Dict, Literal
from config.models.annotations.feature import FeatureModel
from config.models.attributes import AttributeValueModel
from config.models.feature import FeatureNeoModel

class MutationPositionModel(BaseModel):
    attribute_value : AttributeValueModel
    aa_position : Optional[List[int]] = None 
    substitution : Optional[str] = None
    aa : Optional[List[str]] = None 
    
class GenotypeModel2(BaseModel):
    label : str # a unique string 
    text : str # The name of the genotype 
    proteome_tag : str 
    features : Optional[List[FeatureModel|FeatureNeoModel]]
    user_tag : Optional[str] = None
    attributes : List[Dict[str, Union[List[Union[FeatureModel|FeatureNeoModel,AttributeValueModel]],Dict[str,MutationPositionModel]]]]#Union[List[Union[FeatureModel,AttributeValueModel]],MutationPositionModel]]]
    tag : str = None
    
    @field_validator("tag", mode="after")
    def check_tag(cls,v : str):
        
        if v is None and cls.label is not None:
            return cls.label 
        
        return v 
    
    
    
class MinimalGenotypeModel(BaseModel):
    attribute_tag : str = "att_genotype"
    tag : str 
    text : str 
    proteome_tag : str 
    




class ProteinMutation(BaseModel):
    id : int 
    tag : Literal["att_protein_mutation:frameshift","att_protein_mutation:flag","att_protein_mutation:insertion","att_protein_mutation:truncation","att_protein_mutation:none","att_protein_mutation:gfp"]
    start : int|None #amino acid start,is always given in C-term direction, for N-term tag for example give 0, for C-term the end amino acid sequence, please note that is not the index and starts at 1 not at 0.  can only be  nOne, it tag is "att_protein_mutation:none"
    end : int|None #amino acid end 
    sequence : str|None #amino acids to be added or substituted (e.g. insertion or substitution)
    
class GeneModificationModel(BaseModel):
    tag : str #feature tag (e.g. Uniprot ID )
    zygosity : Literal["att_gene_zygosity:(+/+)","att_gene_zygosity:(-/+)","att_gene_zygosity:(-/-)","att_gene_zygosity:unknown"] #traits from att_gene_zygosity 
    gene_engineering : Literal["att_gene_engineering:ko","att_gene_engineering:ki"] #traits from att_gene_engineering 
    editing_method : Literal["att_gene_editing_method:crispr","att_gene_editing_method:biggybac"] #traits from att_gene_editing_method 
    mutations : List[ProteinMutation]
    

class GenotypeModel(BaseModel):
    id : int 
    created_at : int #timestamp 
    tag : str 
    text : str 
    description : str|None 
    publication : str|None #pubmed id 
    user_tag : str|None # user who created the genotype 
    features : List[str] #list of uniprot ids of the features that are affected by the genotype 
    proteome_tags : List[str] #list of proteomes that are affected, for example it might be a ko in a human cellline, but re-epxressing a mouse protein, this info could be retireved by the features itself 
    gene_modifications : List[GeneModificationModel]
    
    

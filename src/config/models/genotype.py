from pydantic import BaseModel, field_validator


from typing import Optional, Union, List, Dict 
from config.models.annotations.feature import FeatureModel
from config.models.attributes import AttributeValueModel

class MutationPositionModel(BaseModel):
    attribute_value : AttributeValueModel
    aa_position : Optional[List[int]] = None 
    substitution : Optional[str] = None
    aa : Optional[List[str]] = None 
    
class GenotypeModel(BaseModel):
    label : str # a unique string 
    text : str # The name of the genotype 
    proteome_id : str 
    features : Optional[List[FeatureModel]]
    attributes : List[Dict[str, Union[List[Union[FeatureModel,AttributeValueModel]],Dict[str,MutationPositionModel]]]]#Union[List[Union[FeatureModel,AttributeValueModel]],MutationPositionModel]]]
    
    
    @field_validator("proteome_id")
    def check_proteome_id(v : str) -> str:
        if not v.startswith("UP"):
            return ValueError("proteome_id must start with UP following Uniprot's reference proteome labeling.")
        return v 


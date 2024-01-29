from pydantic import BaseModel, field_validator


from typing import Optional, Union, List, Dict 
from config.models.annotations.feature import FeatureModel
from config.models.attributes import AttributeValueModel

class GenotypeModel(BaseModel):
    label : str # a unique string 
    text : str # The name of the genotype 
    proteome_id : str 
    features : Optional[List[FeatureModel]]
    attributes : List[Dict[str, List[Union[FeatureModel,AttributeValueModel]]]]
    
    
    @field_validator("proteome_id")
    def check_proteome_id(v : str) -> str:
        if not v.startswith("UP"):
            return ValueError("proteome_id must start with UP following Uniprot's reference proteome labeling.")
        return v 


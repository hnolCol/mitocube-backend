from pydantic import BaseModel, field_validator


from typing import Optional, Union, List, Dict 
from config.models.annotations.feature import FeatureModel
from config.models.attributes import AttributeValueModel
from config.models.feature import FeatureNeoModel

class MutationPositionModel(BaseModel):
    attribute_value : AttributeValueModel
    aa_position : Optional[List[int]] = None 
    substitution : Optional[str] = None
    aa : Optional[List[str]] = None 
    
class GenotypeModel(BaseModel):
    label : str # a unique string 
    text : str # The name of the genotype 
    proteome_tag : str 
    features : Optional[List[FeatureModel|FeatureNeoModel]]
    user_tag : Optional[str] = None
    attributes : List[Dict[str, Union[List[Union[FeatureModel|FeatureNeoModel,AttributeValueModel]],Dict[str,MutationPositionModel]]]]#Union[List[Union[FeatureModel,AttributeValueModel]],MutationPositionModel]]]
    
    
    
class MinimalGenotypeModel(BaseModel):
    attribute_tag : str = "att_genotype"
    tag : str 
    text : str 
    proteome_tag : str 
    


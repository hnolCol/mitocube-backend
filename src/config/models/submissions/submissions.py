import time

from datetime import datetime 
from typing import List, Dict, Optional, Union
from pydantic import AnyUrl
from pydantic import BaseModel 
from pydantic import Field
from pydantic import field_validator
from pydantic import field_serializer

from config.models.user import PublicUser
from config.models.attributes import AttributeModel, AttributeValueModel
from config.models.submissions.timeline import TimeLineModel, TimeLineEntryModel
from config.models.submissions.runs import RunListModel
from config.models.genotype import GenotypeModel, MinimalGenotypeModel
from config.models.annotations.feature import FeatureModel
from config.models.unit import UserUnitInput, InputModel
from config.models.feature import FeatureNeoModel

from config.settings.metatexts import MetaTexts
from config.enums.states import SubmissionStatesEnums
from services.random_generators import get_random_string

from services.date import get_time_stamp



class SubmissionLink(BaseModel):
    """"""
    id : str 
    url : AnyUrl
    comment : str = None


    @field_serializer("url", mode="plain")
    def url_to_string(v : AnyUrl):
        return str(v)
    
class SampleAttribute(BaseModel):
    """_summary_

    Parameters
    ----------
    attribute : AttributeModel 
        The attribute model 
    name : str 
        The name of the samples attributes
    """
    attribute : AttributeModel
    name : str 


class MinimalMetadataModel(BaseModel):
    ""
    tag : str 
    title : str 
    state : SubmissionStatesEnums
    created_at : float 
    n_samples : int 
    n_replicates : int 
    user_tag : Optional[str] = None 
    proteome_tags : List[str]
    has_datatable : bool 
    
class MinimalMetadataResponseModel(MinimalMetadataModel):
    "" 
    

class NewSubmissionModel(BaseModel):
    """
    Model to handle submissions from the ui. 

    Parameters
    ----------


    """
    created_on : float = Field(..., default_factory= get_time_stamp)
    sampleNames : List[str]
    replicates : List[int]
    collaborators : List[PublicUser]
    attributeTable : List[Dict[str,List[Union[AttributeValueModel,FeatureModel,FeatureNeoModel]]]]
    metatext : Dict[str,str]
    links : List[SubmissionLink]
    genotypes : Optional[List[List[MinimalGenotypeModel]]] = None
    tag : str = Field(...,min_length=10, max_length=12)
    title : str 
    datasetAttributeValues : Dict[str,List[Union[AttributeValueModel,FeatureModel,FeatureNeoModel]]]
    datasetAttributes : List[AttributeModel]
    samplesAttributes : List[AttributeModel]
    timeline : TimeLineModel = Field(...,default_factory=TimeLineModel)
    includes_data : bool = False 
    data_array : List[List[float|None]] = None 
    data_sample_names : List[str] = None
    data_index : List[str|None] = None 
    datasetAttributeInput : Dict[str, Dict[str,UserUnitInput]] = None 
    samplesAttributesInput : Dict[str,List[Dict]] = None  #[str,UserUnitInput]
    
    
    @field_validator("datasetAttributeInput", mode="after")
    def validate_dataset_attribute_input(cls, v : Dict|None, config):
        if v is None: return
        return v
    
    # @field_validator("samplesAttributesInput", mode="after")
    # def validate_sample_attribute_input(cls, v : Dict[str,List[Dict]]|None, config):
    #     """"""
    #     if v is None: return
        
    #     n_samples = len(cls.sampleNames)
    #     input_with_values = [[xi for xi  in vi if len(xi) > 0] for vi in v.values()]
    #     if any(n == n_samples for n in input_with_values):
    #         raise ValueError("The length of the sample attribute input (units) must match the length of samples.")
        
    #     return v 
 
    @field_validator("metatext")
    def validate_meta_text(cls, v : Dict[str,str], config):
        """"""
        meta_settings = MetaTexts()
        #check first presents of required metatexts
        
        required_titels_tags = [tag for tag, required in meta_settings.required.items() if required and meta_settings.allowed_for_state[tag] == 0]
        
        if not all(tag in v for tag in required_titels_tags):
            raise ValueError(f"Not all required metatexts found. {required_titels_tags}")
        ## check for minimal length 
        min_length_not_met = [tag for tag, min_length in meta_settings.min_text_length.items() if tag in v and len(v[tag]) < min_length]
        if len(min_length_not_met) > 0:
            raise ValueError(f"Minimal length not met for {min_length_not_met}")

        return v 
    
class NewSubmissionModelBACKUP(BaseModel):
    """
    Model to handle submissions from the ui. 

    Parameters
    ----------


    """
    created_on : float = Field(..., default_factory= time.time)
    sampleNames : List[str]
    replicates : List[int]
    collaborators : List[PublicUser]
    attributeTable : List[Dict[str,List[Union[AttributeValueModel,FeatureModel]]]]
    metatext : Dict[str,str]
    links : List[SubmissionLink]
    genotypes : Optional[List[List[GenotypeModel]]] = None
    label : str = Field(...,min_length=10, max_length=12)
    title : str 
    datasetAttributeValues : Dict[str,List[Union[AttributeValueModel,FeatureModel]]]
    datasetAttributes : List[AttributeModel]
    samplesAttributes : List[AttributeModel]
    timeline : TimeLineModel = Field(...,default_factory=TimeLineModel)
    includes_data : bool = False 
    data_array : List[List[float|None]] = None 
    data_sample_names : List[str] = None
    data_index : List[str|None] = None 
 
    @field_validator("metatext")
    def validate_meta_text(cls, v : Dict[str,str], config):
        """"""
        meta_settings = MetaTexts()
        #check first presents of required metatexts
        
        required_titels_tags = [tag for tag, required in meta_settings.required.items() if required and meta_settings.allowed_for_state[tag] == 0]
        
        if not all(tag in v for tag in required_titels_tags):
            raise ValueError(f"Not all required metatexts found. {required_titels_tags}")
        ## check for minimal length 
        min_length_not_met = [tag for tag, min_length in meta_settings.min_text_length.items() if tag in v and len(v[tag]) < min_length]
        if len(min_length_not_met) > 0:
            raise ValueError(f"Minimal length not met for {min_length_not_met}")

        return v 
    
class UpdateDatasetAttributesInSubmission(BaseModel):
    """Update submission model"""
    modified_on : float = Field(..., default_factory= get_time_stamp)
    datasetAttributeValues : Dict[str,List[Union[AttributeValueModel,FeatureModel]]]
    datasetAttributes : List[AttributeModel]


class SampleAttributeInput(BaseModel):
    attribute_value_tag : str 
    sample_index : Optional[int] = None 
    input : List[InputModel]

class SampleAttributeFromDB(BaseModel):
    """"""
    name : str
    values : Dict[str,List[int]]
    
class SampleAttributesResponse(BaseModel):
    """"""
    name : str
    values : Dict[str,List[int]]
    attribute_values : Dict[str,Union[AttributeValueModel,FeatureModel]]

class DatasetSubmissionModel(BaseModel):
    ""
    created_on : float
    modified_on : Optional[float] = None
    state : SubmissionStatesEnums
    label : Optional[str] = None
    tag : str
    title : str
    user_tag : str
    collaborators : List[str]
    replicates : List[int]
    sample_names : List[str]
    n_samples : int
    metatext : Dict[str,str] = {}
    dataset_attributes : Dict[str,List[str]]
    samples_attributes : Dict[str,Dict[str,List[int]]]
    samples_genotypes : Dict[str,List[int]] = Field(...,default_factory=dict)
    links : List[SubmissionLink] = []
    timeline : TimeLineModel = Field(...,default_factory=TimeLineModel)
    runlist : Optional[RunListModel] = None 
    samples_attributes_input : Optional[Dict[str,List[SampleAttributeInput]]] = None #input in terms of 'by the user' If input is allowed, it is defined in the attributes.


class DatasetSubmissionResponseModel(DatasetSubmissionModel):
    ""
    dataset_attributes : Dict[str,List[Union[AttributeValueModel,FeatureModel]]]
    #samples_attributes : Dict[str,SampleAttributesResponse]
    samples_attributes_by_sample : Dict[str, Dict[str,List[Union[AttributeValueModel,FeatureModel]]]]
    attributes : Dict[str,AttributeModel] #The attributes by tags 
    attribute_values_by_tag : Dict[str,Union[AttributeValueModel,FeatureModel]]
    genotypes : Dict[str, GenotypeModel] = Field(..., default_factory = {})
    

class SubmissionUserCountResponse(BaseModel):
    user_label : str
    submission_labels : List[str]
    submission_count : int
    
class SubmissionCountResponse(BaseModel):
    tags : List[str]
    count : int

class SubmissionQueryResponse(BaseModel):
    submissions : List[MinimalMetadataModel]
    tags : List[str]
    query_count : int
    total_count : int 
        
class SubmissionByUserResponse(BaseModel):
    user_tag : str
    tags : List[str]
    count : int
    
class SubmissionIDResponse(BaseModel):
    """BaseModel for an API ID Submission response"""
    id: str = Field(default_factory= lambda : get_random_string(N=10))
    created_on : datetime = Field(default_factory= datetime.now)



class DatasetAttributesResponse(BaseModel):
    """BaseModel for the response of dataset attributes
    for a submission. 

    Parameters
    ----------
    tag - submission tag 
    
    """
    tag : str
    tags : Dict[str,List[str]]
    attributes : Dict[str,AttributeModel]
    attribute_values : Dict[str,AttributeValueModel|FeatureNeoModel]
    

    @field_validator('attributes', mode='before')
    def transform_attributes(cls, attributes : List[AttributeModel]|Dict[str,AttributeModel|FeatureNeoModel]) -> Dict[str,AttributeModel]:
        "Transform list of attributes to a dict -> attributes by tag" 
        if isinstance(attributes,list):
            return dict([(a.tag,a) for a in attributes])
        elif isinstance(attributes,dict):
            return attributes 
        raise TypeError("Attributes must either be a list or dict. ")

    @field_validator('attribute_values', mode='before')
    def transform_attribute_values(cls, attribute_values : List[AttributeValueModel|FeatureNeoModel]|Dict[str,AttributeModel|FeatureNeoModel]) -> Dict[str,AttributeValueModel|FeatureNeoModel]:
        "Transform list of attributes to a dict -> attributes by tag" 
        if isinstance(attribute_values,list):
            return dict([(av.tag,av) for av in attribute_values])
        elif isinstance(attribute_values,dict):
            return attribute_values 
        raise TypeError("Attributes must either be a list or dict. ") 
        
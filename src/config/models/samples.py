from pydantic import BaseModel


class SampleModel(BaseModel):
    created_at : float 
    tag : str 
    text : str = None 
    index : int = None 
    
    
class SampleResponseModel(SampleModel):
    pass 
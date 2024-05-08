from pydantic import BaseModel


class FulltextSearchResult(BaseModel):
    tag : str 
    score : float 
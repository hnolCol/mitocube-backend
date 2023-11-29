
from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings
from pydantic import DirectoryPath


class Annotations(BaseSettings):
    """
    """
    path_annotations : DirectoryPath = "/Users/hnolte/Documents/GitHub/mitocube-backend/resources/annotations"
    annotation_file_seperator : str = "\t"
    annotation_feature_id_columns : List[str] = ["Entry","Key", "Uniprot ID", "Protein ID", "Uniprot"]
    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def  get_annotation_settings():
    """
    Returns the Annotation Settings. 
    """
    return Annotations() 
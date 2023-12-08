
from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings
from pydantic import DirectoryPath


class AnnotationSettings(BaseSettings):
    """"""
    path_features : DirectoryPath = "/Users/hnolte/Documents/GitHub/mitocube-backend/resources/features"
    file_features : str = "data.txt"
    seperator_features : str = "\t"
    file_features_column_mappings: str = "mappings.txt"

    path_annotations : DirectoryPath = "/Users/hnolte/Documents/GitHub/mitocube-backend/resources/annotations"
    file_annotations : str = "data.txt"
    info_annotations : str = "info.txt"
    seperator_annotations : str = "\t"
    file_annotations_column_mappings: str = "mappings.txt"

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_annotation_settings():
    """
    Returns the Annotation Settings. 
    """
    return AnnotationSettings()

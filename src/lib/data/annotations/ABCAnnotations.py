from abc import abstractmethod
from collections import OrderedDict

import pandas as pd 

from lib.data.DesignPatterns import SingletonABCMeta

from config.settings.annotations import get_annotation_settings
from config.settings.general import get_general_settings 
from config.settings.db import get_db_settings

GENERAL_SETTINGS = get_general_settings() 
DB_SETTINGS = get_db_settings()
class Annotations(metaclass = SingletonABCMeta):

    def __init__(self) -> None:
        
        self._cached_annotations = OrderedDict() 

    
    @abstractmethod
    def get_annotations_by_featureID(self, feature_id : str, organism_id : str) -> pd.DataFrame:
        """Returns the annotations by feature id"""

    @staticmethod
    def get_annotation_db():
        ""
        if DB_SETTINGS.db_handler == "pandafiles":
            from lib.data.annotations.FileAnnotations import PandaAnnoations
            return PandaAnnoations()
        



import pandas as pd 

from pydantic import BaseModel, Field, field_serializer
from typing import List, Dict, Any, Tuple, Literal 

from threading import Lock
from abc import abstractmethod

from lib.DesignPatterns import SingletonABCMeta
from config.models.submissions.submissions import SubmissionCountResponse
from config.settings.db import get_db_settings

DB_SETTTINGS = get_db_settings()


class MCDatabaseHelper(metaclass=SingletonABCMeta):
    def __init__(self, instrument_attribute_tag : str = "att_ms_name") -> None:
        """"""
        pass 
    
    @staticmethod
    def getDatabaseHelper():
        if DB_SETTTINGS.db_handler == "pandafiles":
            from lib.database_helper.PandaHelper import PandaDatabaseHelper
            return PandaDatabaseHelper()
        raise ValueError("db-handler is unknown.")
    
    @abstractmethod
    def get_all_labels(self):
        pass 
    
    @abstractmethod
    def get_attribute_value_tags_by_labels(self, 
                                           labels : str, 
                                           split_string = ";", 
                                           join = Literal["inner","outer"], 
                                           count : bool = True, 
                                           attribute_value_subset : str = None, 
                                           attribute_subset : str = None) -> Tuple[set,Dict[str|int,SubmissionCountResponse]]:
        
        pass
        
    @abstractmethod
    def get_attribute_tags_by_labels(self, labels : str, split_string = ";", join = Literal["inner","outer"], count : bool = True) -> Tuple[set,Dict[str|int,SubmissionCountResponse]]:
        pass 
        
    @abstractmethod
    def get_metadata_count(self):
        pass 
    
    @abstractmethod
    def get_datatable_count(self):
        pass
    
    @abstractmethod
    def get_instruments(self):
        pass 
        
    @abstractmethod
    def get_instrument_first_use(self, instrument_tag : str = None) -> float|Dict[str,float]:
        pass 
    
    @abstractmethod  
    def get_number_features(self) -> int:
        pass 
    
    @abstractmethod
    def get_number_genotypes(self) -> int:
        pass 
    
    @abstractmethod
    def get_sample_number_by_instrument(self) -> Dict[str,List[int]]:
        pass 
    
    @abstractmethod
    def get_labels(self, state : int|str = None, user_label : str = None, feature_key : str = None, attribute_tag : str = None, attribute_value_tag : str = None, genotype_label : str = None, join : Literal["inner","outer"] = "inner") -> set:
        pass
        
    @abstractmethod
    def get_organisms_by_label(self, labels : str, split_string = ";", join = Literal["inner","outer"], count : bool = True) -> Tuple[set,Dict[str|int,SubmissionCountResponse]]:
        pass
    
    @abstractmethod
    def get_labels_by_instrument(self, instrument_tag : str) -> List[Dict]:
        pass
        
    @abstractmethod
    def get_labels_by_organism(self, organism_tag : str):
        pass
    
    @abstractmethod
    def get_labels_by_search_string(self, query : str, subset : set = None) -> List[str]:
        pass
    
    @abstractmethod         
    def get_labels_by_state(self, state : int|str) -> set:
        pass
    
    @abstractmethod    
    def get_labels_by_feature(self, feature_key : str) -> set:
        pass
    
    @abstractmethod
    def get_label_count_by_feature(self, k_subset : set = None, label_subset : set = None) -> Dict[str|int,SubmissionCountResponse]:
        pass
    
    @abstractmethod
    def get_labels_by_attribute_tag(self, attribute_tag : str) -> set:
        pass 
    
    @abstractmethod
    def get_label_count_by_attribute_tag(self, k_subset : set = None, label_subset : set = None) -> Dict[str|int,SubmissionCountResponse]:
        pass
    
    @abstractmethod
    def get_labels_by_attribute_value_tag(self, attribute_value_tag : str ) -> set:
        pass
    
    @abstractmethod
    def get_label_count_by_attribute_value_tag(self, k_subset : set = None, label_subset : set = None) -> Dict[str|int,SubmissionCountResponse]:
        pass 
    
    @abstractmethod
    def get_labels_by_genotype_label(self, genotype_label : str) -> set:
        pass 
    @abstractmethod
    def get_label_count_by_genotype(self, k_subset : set = None, label_subset : set = None) -> Dict[str|int,SubmissionCountResponse]:
        pass 
    
    @abstractmethod
    def get_label_count_by_user(self, k_subset : set = None, label_subset : set = None) -> Dict[str|int,SubmissionCountResponse]:
        """_summary_
        """
    @abstractmethod
    def get_label_count_by_state(self, k_subset : set = None, label_subset : set = None):
        pass
        
    @abstractmethod
    def get_labels_by_user_label(self, user_label : str) -> set:
        pass
           
    @abstractmethod
    def get_label_count_by(self, by : Literal["feature","state","user","attribute_value_tag","attribute_tag","genotype"] = None, k_subset : set = None, label_subset : set = None) -> Dict[str|int,SubmissionCountResponse]:   
        pass
        
    @abstractmethod
    def get_rel_variance_by_feature(self, feature_key : str, labels : str = None) -> pd.DataFrame:
        pass
       
    @abstractmethod
    def get_abundance_by_feature(self,feature_key : str, labels : str = None) -> pd.DataFrame:
        pass 
    
    @abstractmethod
    def update(self):
        """
        Triggers a reload of the database.
        """
        
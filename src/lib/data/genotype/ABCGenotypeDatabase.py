
import pandas as pd 
from typing import List, Dict, Any, Tuple, Optional

from abc import abstractmethod

from lib.DesignPatterns import SingletonABCMeta  # , ExpiringValue
from config.settings.db import get_db_settings
from config.models.genotype import GenotypeModel

DB_SETTTINGS = get_db_settings()


class MCGenotypes(metaclass=SingletonABCMeta):
    def __init__(self) -> None:
        """"""
        pass 
    
    @staticmethod
    def getGenotypeDatabase():
        if DB_SETTTINGS.db_handler == "pandafiles":
            from lib.data.genotype.PandaGenotype import PandaFileGenotype
            return PandaFileGenotype()
        raise ValueError("db-handler is unknown.")
    
    @abstractmethod
    def add(self) -> bool:
        """"""
    
    @abstractmethod
    def find(self,query : str) -> List[GenotypeModel]:
        """_summary_

        Parameters
        ----------
        query : str
            A string that searches in the text prop of the GenotypeModel

        Returns
        -------
        List[GenotypeModel]
            _description_
        """
    
    @abstractmethod
    def get(self) -> List[GenotypeModel]|GenotypeModel:
        """"""    
    
    @abstractmethod
    def delete(self, label : str) -> bool:
        """_summary_

        Parameters
        ----------
        label : str
            _description_

        Returns
        -------
        bool
            _description_
        """
        
    
    @abstractmethod
    def update(self):
        """
        Triggers a reload of the database.
        """
        
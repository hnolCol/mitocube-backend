
import pandas as pd 
import typing
from typing import List, Dict, Any, Tuple, Optional
from pydantic import BaseModel, Field, field_serializer
from threading import Lock
from abc import abstractmethod

from lib.DesignPatterns import SingletonABCMeta  # , ExpiringValue
from config.settings.db import get_db_settings

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
    def get(self) -> List:
        """"""    
    
    @abstractmethod
    def update(self):
        """
        Triggers a reload of the database.
        """
        
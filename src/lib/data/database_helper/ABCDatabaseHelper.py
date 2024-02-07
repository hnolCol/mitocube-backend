
import pandas as pd 
import typing
from typing import List, Dict, Any, Tuple, Optional
from pydantic import BaseModel, Field, field_serializer
from threading import Lock
from abc import abstractmethod

from lib.DesignPatterns import SingletonABCMeta  # , ExpiringValue
from config.settings.db import get_db_settings

DB_SETTTINGS = get_db_settings()


class MCDatabaseHelper(metaclass=SingletonABCMeta):
    def __init__(self) -> None:
        """"""
        pass 
    
    @staticmethod
    def getDatabaseHelper():
        if DB_SETTTINGS.db_handler == "pandafiles":
            from lib.data.database_helper.PandaHelper import PandaDatabaseHelper
            return PandaDatabaseHelper()
        raise ValueError("db-handler is unknown.")
    
    @abstractmethod
    def update(self):
        """
        Triggers a reload of the database.
        """
        
from __future__ import annotations

from abc import abstractmethod, ABC
# from datetime import timedelta
from typing import List, Dict, Optional, Tuple, Literal  # , Any
from deprecated import deprecated
import pandas as pd

from config.models.unit import  UnitTypeResponseModel
from config.models.user import UserModel


class UnitTypesABC(ABC):
    
    
    @abstractmethod
    def has_attribute_unit_types(self, attribute_tag : str) -> bool:
        """Checks if the given attribute has a unit. If the attribute
        tag is not associated with an attribute, still just False should be
        returned. """
        
    @abstractmethod
    def get_unit_types(self) -> List[str]:
        "" 
        
    @abstractmethod
    def get_units(self, tags : List[str]) -> UnitTypeResponseModel:
        "Returns the units associated with a unit type"
        
         

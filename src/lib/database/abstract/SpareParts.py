from __future__ import annotations
from abc import abstractmethod, ABC

from typing import List, Literal
from deprecated import deprecated
from config.models.spareparts import SparepartResponseModel


class SparePartsABC(ABC):
    """
    
    Parameters
    ----------
    ABC : _type_
        The abstract class 
    """
    @abstractmethod
    def get(self, tag : str) -> SparepartResponseModel:
        ""
        
    @abstractmethod
    def find(self, search_string : str) -> List[str]:
        "" 
        
    
    
    
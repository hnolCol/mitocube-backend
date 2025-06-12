from __future__ import annotations
from abc import abstractmethod, ABC

from typing import List, Dict, Optional, Tuple
from deprecated import deprecated


class InstrumentsABC(ABC):

    @abstractmethod 
    def get(self, tags : List[str] = None) -> List:
        """Returns the instruments

        Parameters
        ----------
        tags : List[str]
            List of instrument tags, defaults to None. If None then
            all available instruments will be returned. 

        Returns
        -------
        List[InstrumentModel]
            
        """
        
        
    @abstractmethod
    def get_samples_by_instrument(self, tags : List[str]) -> Dict:
        "" 
        






    
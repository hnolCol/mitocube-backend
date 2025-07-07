from __future__ import annotations
from abc import abstractmethod, ABC

from typing import List, Dict, Optional, Tuple
from deprecated import deprecated

from config.models.instruments import InstrumentStateHistoryModel, InstrumentsStateResponseModel, InstrumentStateModel

class InstrumentStatesABC(ABC):
    
    
    @abstractmethod
    def get(self, tag : str = None) -> InstrumentStateModel:
        ""
        
    @abstractmethod
    def get_instrument_state(self, instrument_tag : str, limit : int = 1) -> List[InstrumentsStateResponseModel]:
        ""
    @abstractmethod
    def get_history(self, instrument_tag : str, limit : int = None) -> List[InstrumentStateHistoryModel]:
        "Returns the history of states for a given instrument"
        
    @abstractmethod
    def find(self, search_string : str = None) -> List[str]:
        "Returns a list of instrument state tags"
    
    @abstractmethod
    def insert(self, state : Dict):
        "Insert a new instrument state to the database."
    
    @abstractmethod
    def set(self, tag : str, instrument_tag : str):
        "Sets the instrument in the state given by its tag."

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
        






    
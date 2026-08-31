from __future__ import annotations
from abc import abstractmethod, ABC

from typing import List, Dict, Optional, Tuple
from deprecated import deprecated
import pandas as pd 
from config.models.instruments import InstrumentStateHistoryModel, InstrumentsStateResponseModel, InstrumentStateModel

class InstrumentStatesABC(ABC):
    
    
    @abstractmethod
    def exists(self, tag : str) -> bool:
        ""
    
    @abstractmethod
    def get(self, tag : str = None) -> InstrumentStateModel:
        ""
        
    @abstractmethod
    def get_instrument_state(self, instrument_tag : str, limit : int = 1) -> List[InstrumentsStateResponseModel]:
        ""
    @abstractmethod
    def get_state_durations(self, instrument_tag : str, limit : int = None) -> List[InstrumentStateHistoryModel]:
        "Returns the history of states for a given instrument"

    @abstractmethod
    def get_fractional_state_durations(self, instrument_tag : str = None, state_tag : str = None, timestamp_min : float = None, timestamp_max : float = None, limit : int = None) -> pd.DataFrame:
        "Returns the history of states for a given instrument as a fraction of the total time."
        
    @abstractmethod
    def find(self, search_string : str = None) -> List[str]:
        "Returns a list of instrument state tags"
    
    @abstractmethod
    def insert(self, state : Dict):
        "Insert a new instrument state to the database."
    
    @abstractmethod
    def set_state(self, tag : str, instrument_tag : str):
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
    def get_types(self, limit: int = 50) -> List[dict]:
        """Returns all the instrument type tags with their display text"""

        
    @abstractmethod
        
    def get_samples_by_instrument(self, tags: List[str] = None) -> List[dict]:
        """Returns sample counts per instrument, grouped by submission, via the runlist path.
        Each submission's current state is included."""

    @abstractmethod
    def get_overview(self, tags: List[str] = None) -> List[dict]:
        """Per-instrument summary: current state + per-submission sample breakdown."""
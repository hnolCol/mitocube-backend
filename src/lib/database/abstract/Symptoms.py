from __future__ import annotations
from abc import abstractmethod, ABC

from typing import List, Literal
from deprecated import deprecated



class SymptomABC(ABC):
    """
    Symptoms describe a problem of the instrumentation, usually a LC-MS/MS system,
    but in principle any kind of the instrument problem may be described by a symptom. 

    Parameters
    ----------
    ABC : _type_
        The abstract class 
    """
    
    def get(self, instrument_tag : str,  tags : List[str] = None) -> list:
        """Returns symptoms in the database. 
        If tags is None, all symptoms will be returned. 

        Parameters
        ----------
        instrument_tag : str 
            The instrument tag for which the symptom is defined. For example, by default 
            problems/symptoms could be attributed to a Liquid Chromatography (LC) or to a mass 
            spectrometer.
            
        tags : List[str], optional
            _description_, by default None

        Returns
        -------
        list
            List of symptoms 
        """
        
        
    
    
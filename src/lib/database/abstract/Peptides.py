from __future__ import annotations

from abc import abstractmethod, ABC
# from datetime import timedelta
from typing import List, Dict, Optional, Tuple, Literal  # , Any
from deprecated import deprecated
import pandas as pd
from config.models.performance import QCPeptidesModel, QCRunModel, QCPeptideModel

class PeptidesABC(ABC):
    """Abstract class to handle peptides.
    For peptides and proteins, instead of a random string as a tag, 
    we simply use the amino acid sequence and the uniprot key. 
    """
    
    @abstractmethod
    def exists(self, tag : str) -> bool:
        """Checks if a given tag is associates with a peptide (e.g. sequence) 

        Parameters
        ----------
        tag : str
            The peptide sequence/tag 

        Returns
        -------
        bool
            If the tag is associated with a peptide 
        """
        
    @abstractmethod
    def set_qc_peptides(self, peptides : QCPeptidesModel, join : bool = True):
        "" 
    
    # @abstractmethod
    # def get(self, tags : List[str] = None, limit : int = 10):
    #    ""
        
    # @abstractmethod
    # def insert(self) -> bool:
        
        
    # @abstractmethod
    # def delete(self, tag : str) -> bool:
    #     ""
    # @abstractmethod
    # def update(self, tag : str) -> bool:
        
    
    

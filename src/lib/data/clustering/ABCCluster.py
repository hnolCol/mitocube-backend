

from abc import abstractmethod, ABC 
from typing import Tuple
 
import pandas as pd 
class DatasetClustering(ABC):
    
    def __init__(self, datatable : pd.DataFrame) -> None:
        """
        """
        self._datatable = datatable
        
    @abstractmethod
    def get_clusters(self,*args, **kwargs) -> Tuple[pd.DataFrame,pd.DataFrame]:
        """_summary_
        """
    
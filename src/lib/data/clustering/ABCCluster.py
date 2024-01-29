

from abc import abstractmethod, ABC 
from typing import Tuple
from lib.data.dataset.ABCDataset import MCDataset 
import pandas as pd 
class DatasetClustering(ABC):
    
    def __init__(self, dataset : MCDataset) -> None:
        """
        """
        self._dataset = dataset
        
    def get_clusters(self,*args, **kwargs) -> Tuple[pd.DataFrame,pd.DataFrame]:
        """_summary_
        """
    
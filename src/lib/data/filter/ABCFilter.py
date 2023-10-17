
from abc import abstractmethod, ABC 
import pandas as pd 

from lib.data.dataset.ABCDataset import MCDataset


class DatasetFilter(ABC):
    """
    """
    def __init__(self, dataset : MCDataset) -> None:
        """
        """
        self._dataset = dataset

    @abstractmethod
    def get_indices(self) -> pd.Index:
        """
        Applies a filtering and returns the indices that match.
        """
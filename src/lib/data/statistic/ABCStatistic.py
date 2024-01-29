from abc import abstractmethod, ABC 
import pandas as pd 

from lib.data.dataset.ABCDataset import MCDataset


class DatasetStatistic(ABC):
    """
    Abstract Class for a statistical test.

    Parameters
    ----------
    dataset : MCDataset
        The dataset to be used for the statitiscal test. 

    Methods
    -------
    get_indices()
        Returns the pd.Index of the dataset data that match the filtering.     

    """
    def __init__(self, dataset : MCDataset) -> None:
        """
        """
        self._dataset = dataset
        self._metadata = self._dataset.getMetaJson()

    @abstractmethod
    def get_stats(self) -> pd.Index:
        """
        Applies a filtering and returns the indices that match.
        """
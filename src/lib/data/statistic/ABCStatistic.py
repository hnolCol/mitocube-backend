from abc import abstractmethod, ABC 
import pandas as pd 




class DatasetStatistic(ABC):
    """
    Abstract Class for a statistical test.

    Parameters
    ----------
    dataset : pd.DataFrame
        The dataset to be used for the statitiscal test. 

    Methods
    -------
    get_indices()
        Returns the pd.Index of the dataset data that match the filtering.     

    """
    def __init__(self, datatable : pd.DataFrame, sample_attribute_map : pd.DataFrame) -> None:
        """
        """
        self._datatable = datatable
        self._sample_attribute_map = sample_attribute_map

    @abstractmethod
    def get_stats(self) -> pd.Index:
        """
        Applies a filtering and returns the indices that match.
        """
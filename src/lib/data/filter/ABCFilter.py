
from abc import abstractmethod, ABC 
import pandas as pd 




class DatasetFilter(ABC):
    """
    Abstract Class for a dataset filter. 

    Parameters
    ----------
    dataset : pd.DataFrame
        The dataset to be filtered.

    Methods
    -------
    get_indices()
        Returns the pd.Index of the dataset data that match the filtering.     

    """
    def __init__(self, dataset : pd.DataFrame) -> None:
        """
        """
        self._dataset = dataset

    @abstractmethod
    def get_indices(self) -> pd.Index:
        """
        Applies a filtering and returns the indices that match.
        """
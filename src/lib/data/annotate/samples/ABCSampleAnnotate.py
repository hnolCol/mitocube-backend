
from abc import abstractmethod, ABC 
import pandas as pd 

from lib.data.dataset.ABCDataset import MCDataset

class SampleAnnotation(ABC):
    """
    """
    def __init__(self, dataset : MCDataset) -> None:
        """
        """
        self._dataset = dataset

    @abstractmethod
    def annotate(self) -> pd.DataFrame:
        """
        Annotate the data table and returns a dataframe 
        using the sample names (columns) of the dataset datatable as index
        """

        
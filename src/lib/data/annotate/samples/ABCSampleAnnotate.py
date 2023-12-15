from abc import abstractmethod, ABC
from deprecated import deprecated
import pandas as pd 

from lib.data.dataset.ABCDataset import MCDataset


@deprecated(reason="Please use the MCAttribute, MCDatabase or MCDataset related classes")
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

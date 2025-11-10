from abc import abstractmethod, ABC
from deprecated import deprecated
import pandas as pd 




@deprecated(reason="Please use the MCAttribute, MCDatabase or MCDataset related classes")
class SampleAnnotation(ABC):
    """
    """
    def __init__(self, dataset : pd.DataFrame) -> None:
        """
        """
        self._dataset = dataset

    @abstractmethod
    def annotate(self) -> pd.DataFrame:
        """
        Annotate the data table and returns a dataframe 
        using the sample names (columns) of the dataset datatable as index
        """

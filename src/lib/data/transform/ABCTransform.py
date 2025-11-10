

from abc import abstractmethod, ABC 

from typing import Tuple
import pandas as pd



class DatasetTransform(ABC):
    """
    """
    def __init__(self, dataset : pd.DataFrame) -> None:
        """
        """
        self._dataset = dataset

    @abstractmethod
    def transform(self) -> Tuple:
        """
        Transforms the dataset
        """

    
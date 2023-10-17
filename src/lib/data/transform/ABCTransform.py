

from abc import abstractmethod, ABC 

from typing import Tuple

from lib.data.dataset.ABCDataset import MCDataset


class DatasetTransform(ABC):
    """
    """
    def __init__(self, dataset : MCDataset) -> None:
        """
        """
        self._dataset = dataset

    @abstractmethod
    def transform(self) -> Tuple:
        """
        Transforms the dataset
        """

    
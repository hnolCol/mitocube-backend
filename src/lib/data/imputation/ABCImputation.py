from abc import abstractmethod, ABC 
import pandas as pd 
from typing import Tuple



class DatasetImputation(ABC):
    """
    Abstract Class for an imputation class.

    Parameters
    ----------
    dataset : pd.DataFrame
        The dataset to be used for the imputation 

    Methods
    -------
    get_imputation()
        Returns the datatable with imputation of missing values.  As well as a boolean matrix 
        that indicates the imputed values.

    """
    def __init__(self, dataset : pd.DataFrame) -> None:
        """
        """
        self._dataset = dataset
        self._metadata = self._dataset.getMetaJson()

    @abstractmethod
    def get_imputation(self, sample_attribute_tag : str) -> Tuple[pd.DataFrame,pd.DataFrame]:
        """
        Applies the imputation
        """

import pandas as pd
from lib.data.filter.ABCFilter import DatasetFilter

class NoNaNFilter(DatasetFilter):
    """
    """

    def get_indices(self) -> pd.Index:
        """
        Returns the indices in a dataset that 
        do not contain any missing values (NaN)
        """
        data = self._dataset.getDataTable()
        return data.dropna().index
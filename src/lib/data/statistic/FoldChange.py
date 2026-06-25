import numpy as np
from lib.data.statistic.ABCStatistic import DatasetStatistic
import pandas as pd 
from typing import List
 
 
class FC(DatasetStatistic):
    
    def get_stats(self, data : pd.DataFrame, sample_tags_left : List[str], sample_tags_right : List[str]) -> pd.DataFrame:
        """_summary_

        Parameters
        ----------
        sample_attribute_name : str
            _description_
        """
        if len(sample_tags_left) == 0 or len(sample_tags_right) == 0:
            raise ValueError("Both sample tag lists must contain at least one sample tag.")
        if not set(sample_tags_left).issubset(set(data.columns)) or not set(sample_tags_right).issubset(set(data.columns)):
            raise ValueError("All sample tags must be present in the datatable columns.") 
        
        datatable = self._datatable
    
        X = datatable.loc[:,sample_tags_left].values
        Y = datatable.loc[:,sample_tags_right].values
        
        log2fc = pd.Series(data=np.log2(X.mean(axis=1) - Y.mean(axis=1)), index=datatable.index)
        
        return log2fc
        
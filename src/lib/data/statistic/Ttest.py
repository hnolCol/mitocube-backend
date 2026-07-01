from lib.data.statistic.ABCStatistic import DatasetStatistic
from lib.database.Database import Database
from lib.data.imputation.StandardImputation import StandardImputation
from scipy.stats import ttest_ind, false_discovery_control
import pandas as pd 
import numpy as np 
from typing import List

DB = Database.DB()
class Ttest(DatasetStatistic):
    
    def get_stats(self, 
                  sample_attribute_tag : str, 
                  attribute_value_left : str, 
                  attribute_value_right : str, 
                  within_attribute_tag : List[str] = None,
                  within_attribute_value_tag : List[str] = None,
                  fdr : float = 0.01,
                  suffix : str = "",
                  impute : bool = False,
                  equal_variance : bool = False) -> pd.DataFrame:
        """_summary_

        Parameters
        ----------
        sample_attribute_tag : str
            _description_
        attribute_value_left : str
            _description_
        attribute_value_right : str
            _description_
        within_attribute_tag : str, optional
            _description_, by default None
        within_attribute_value_tag : str, optional
            _description_, by default None
        fdr : float, optional
            _description_, by default 0.01
        suffix : str, optional
            _description_, by default ""
        impute : bool, optional
            _description_, by default False

        Returns
        -------
        pd.DataFrame
            _description_
        """
        

        mapped_sample_index = self._sample_attribute_map
        datatable = self._datatable
        #check if there is a within grouping, then subset the mapped sample names first
        if within_attribute_tag is not None and within_attribute_value_tag is not None:
            for within_attr_tag, within_attr_value_tag in zip(within_attribute_tag,within_attribute_value_tag):
                bool_within = mapped_sample_index.loc[:,within_attr_tag] == within_attr_value_tag
                mapped_sample_index = mapped_sample_index.loc[bool_within]
                
        boolIdx = mapped_sample_index.loc[:,sample_attribute_tag].isin([attribute_value_left,attribute_value_right])
        subset_mapped_sample_index = mapped_sample_index.loc[boolIdx]
        #get the sample index (e.g. column names in the datatable)
        samples_left = subset_mapped_sample_index.loc[subset_mapped_sample_index[sample_attribute_tag] == attribute_value_left].index.values
        samples_right = subset_mapped_sample_index.loc[subset_mapped_sample_index[sample_attribute_tag] == attribute_value_right].index.values
            
        X = datatable.loc[:,samples_left]
        Y = datatable.loc[:,samples_right]
        T,p = ttest_ind(X, Y, nan_policy="omit", axis=1, equal_var=equal_variance)
        p_value_name = f"p-value {suffix}"
        
        
        stats = pd.DataFrame({f"t-value {suffix}" : T, p_value_name : p}, 
                             columns=[f"t-value {suffix}",p_value_name], 
                             index=datatable.index)
        
        stats = stats.dropna(subset=[p_value_name])
        stats.loc[:,f"-log10 p-value {suffix}"] = -np.log10(stats.loc[:,p_value_name])
        stats.loc[:,f"fdr {suffix}"] = false_discovery_control(stats[p_value_name].values)
        stats.loc[:,f"Significant {suffix}"] = stats.loc[:,f"fdr {suffix}"] <= fdr
        stats.loc[:,f"log2 FC {suffix}"] = X.mean(axis=1) - Y.mean(axis=1)
        return stats
        
        
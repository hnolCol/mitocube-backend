from lib.data.statistic.ABCStatistic import DatasetStatistic
from scipy.stats import ttest_ind, false_discovery_control
import pandas as pd 
import numpy as np 
class Ttest(DatasetStatistic):
    def get_stats(self, 
                  sample_attribute_tag : str = "att_compound", 
                  attribute_value_left : str = "att_compound:dmso", 
                  attribute_value_right : str = "att_compound:hydroxyurea", 
                  fdr : float = 0.01,
                  suffix : str = "") -> pd.DataFrame:
        """_summary_

        Parameters
        ----------
        sample_attribute_name : str, optional
            _description_, by default "Treatment"
        attribute_value_left : _type_, optional
            _description_, by default "att_compound:dmso"
        attribute_value_right : _type_, optional
            _description_, by default "att_compound:hydroxyurea"
        fdr : float, optional
            _description_, by default 0.01

        Returns
        -------
        pd.DataFrame
            _description_
        """
        datatable = self._dataset.getDataTable()
        mapped_sample_names, _ = self._dataset.getSamplesAttributes()
        boolIdx = mapped_sample_names.loc[:,sample_attribute_tag].isin([attribute_value_left,attribute_value_right])
        subset_mapped_sample_names = mapped_sample_names.loc[boolIdx]
        #get the sample names (e.g. column names in the datatable)
        samples_left = subset_mapped_sample_names.loc[subset_mapped_sample_names[sample_attribute_tag] == attribute_value_left].index.values
        samples_right = subset_mapped_sample_names.loc[subset_mapped_sample_names[sample_attribute_tag] == attribute_value_right].index.values
        # X1, X2 = X.loc[:,columNamesGroup1], X.loc[:,columNamesGroup2]
        X = datatable.loc[:,samples_left]
        Y = datatable.loc[:,samples_right]
        T,p = ttest_ind(X, Y, nan_policy="omit", axis=1)
        p_value_name = f"p-value {suffix}"
        
        stats = pd.DataFrame({f"t-value {suffix}" : T, p_value_name : p}, 
                             columns=[f"t-value {suffix}",p_value_name], 
                             index=datatable.index).dropna(subset=p_value_name)
        
        stats = stats.dropna(subset=[p_value_name])
        stats.loc[:,f"-log10 p-value {suffix}"] = -np.log10(stats.loc[:,p_value_name])
        stats.loc[:,f"fdr {suffix}"] = false_discovery_control(stats[p_value_name].values)
        stats.loc[:,f"significant {suffix }"] = stats.loc[:,f"fdr {suffix}"] <= fdr
        stats.loc[:,f"log2 FC {suffix}"] = X.mean(axis=1) - Y.mean(axis=1)
        return stats
        # boolIdx, p_adj, _, _ = multipletests(p, alpha=0.05, method=multipleTestMethod)
        # tTestDifference = pd.DataFrame(pd.Series(X1.mean(axis=1) - X2.mean(axis=1), name="x"))
        # tTestDifference["y"] = (-1)*np.log10(p)
        # tTestDifference["s"] = boolIdx
        # return tTestDifference
        
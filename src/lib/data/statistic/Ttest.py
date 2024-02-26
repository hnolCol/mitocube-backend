from lib.data.statistic.ABCStatistic import DatasetStatistic
from lib.data.imputation.StandardImputation import StandardImputation
from scipy.stats import ttest_ind, false_discovery_control
import pandas as pd 
import numpy as np 
class Ttest(DatasetStatistic):
    
    def get_stats(self, 
                  sample_attribute_tag : str, 
                  attribute_value_left : str, 
                  attribute_value_right : str, 
                  within_sample_attribute_tag : str = None,
                  within_sample_attribute_value_tag : str = None,
                  fdr : float = 0.01,
                  suffix : str = "", impute : bool = False) -> pd.DataFrame:
        """_summary_

        Parameters
        ----------
        sample_attribute_tag : str
            _description_
        attribute_value_left : str
            _description_
        attribute_value_right : str
            _description_
        within_sample_attribute_tag : str, optional
            _description_, by default None
        within_sample_attribute_value_tag : str, optional
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
        
        if impute:
            datatable, imputed_bools = StandardImputation(self._dataset).get_imputation(sample_attribute_tag, 
                                                                         within_sample_attribute_tag=within_sample_attribute_tag, 
                                                                         within_sample_attribute_value_tag=within_sample_attribute_value_tag,
                                                                         subset_attribute_value_tags=[attribute_value_left,attribute_value_right])
        else:
            datatable = self._dataset.getDataTable()
        
        mapped_sample_names, _ = self._dataset.getSamplesAttributes()
        #check if there is a within grouping, then subset the mapped sample names first
        if within_sample_attribute_value_tag is not None and within_sample_attribute_value_tag is not None:
            bool_within = mapped_sample_names.loc[:,within_sample_attribute_tag] == within_sample_attribute_value_tag
            mapped_sample_names = mapped_sample_names.loc[bool_within]
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
        
        
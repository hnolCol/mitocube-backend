from lib.data.statistic.ABCStatistic import DatasetStatistic
from scipy.stats import f_oneway, false_discovery_control, zscore
import pandas as pd 
from typing import Tuple

class OneWayANOVA(DatasetStatistic):
    
    def get_stats(self, sample_attribute_name : str = "Treatment", fdr : float = 0.01, dropna : bool = True) -> pd.DataFrame:
        """_summary_

        Parameters
        ----------
        sample_attribute_name : str
            _description_
        """
        mapped_sample_names, sample_attrs = self._dataset.getSamplesAttributes()
        ##just for prototyping, TODO: remove, take simply the first sample attribute
        if sample_attribute_name  not in mapped_sample_names.columns:
            sample_attribute_tag = list(sample_attrs.keys())[0]
        #sample_attributes = self._metadata.samples_attributes
        if sample_attribute_tag in mapped_sample_names.columns:
            grouped_samples = mapped_sample_names.groupby(by=sample_attribute_tag)
            grouped_sample_names = [group_data.index for _, group_data in grouped_samples]
            datatable = self._dataset.getDataTable()
            if dropna:
                datatable = datatable.dropna()
            if datatable.empty: raise ValueError("Nan filtering resulted in an empty datatable.")
            data_for_test = [datatable.loc[:,column_names].values for column_names in grouped_sample_names]
            #returns F-value and p-values
            F,p = f_oneway(*data_for_test,axis=1)
            stats = pd.DataFrame({"F" : F, "p-value" : p}, columns=["F","p-value"], index = datatable.index)
            stats = stats.dropna(subset=["p-value"])
            if stats.empty : raise ValueError("All caluclated p-values were nan. Not enough samples/valid values?")
            stats.loc[:,"fdr"] = false_discovery_control(stats["p-value"].values)
            stats = stats.loc[stats["fdr"] <= fdr,:] #subset at fdr 
            return stats
        return pd.DataFrame()
        
from lib.data.statistic.ABCStatistic import DatasetStatistic
from scipy.stats import f_oneway, false_discovery_control
import pandas as pd 
from scipy.stats import f
from typing import Tuple
import numpy as np 

class OneWayANOVA(DatasetStatistic):
    
    def get_group_validity(self, datatable, grouped_sample_names, min_non_nan):
        counts = np.stack(
            [datatable.loc[:, cols].notna().sum(axis=1).values for cols in grouped_sample_names],
            axis=1
        )
        valid_group = counts >= min_non_nan
        return counts, valid_group


    def nan_f_oneway(self, groups, counts, valid_group):
        """
        groups: list of 2D arrays (n_rows, n_samples_in_group)
        counts, valid_group: from get_group_validity(), shape (n_rows, n_groups)
        """
        n_rows = groups[0].shape[0]

        means = np.stack([
            np.divide(
                np.nansum(g, axis=1),
                counts[:, k],
                out=np.full(n_rows, np.nan, dtype=float),
                where=counts[:, k] > 0
            )
            for k, g in enumerate(groups)
        ], axis=1)
        n_valid_groups = valid_group.sum(axis=1)
        eligible = n_valid_groups >= 2

        counts_v = np.where(valid_group, counts, 0)
        means_v  = np.where(valid_group, means, 0.0)

        N = counts_v.sum(axis=1)
        with np.errstate(invalid="ignore", divide="ignore"):
            grand_mean = (counts_v * means_v).sum(axis=1) / N

        ssb = (counts_v * (means_v - grand_mean[:, None]) ** 2).sum(axis=1)

        ssw = np.zeros(n_rows)
        for k, g in enumerate(groups):
            gm = means[:, k][:, None]
            sq_sum = np.nansum((g - gm) ** 2, axis=1)
            ssw += np.where(valid_group[:, k], sq_sum, 0.0)

        df_between = n_valid_groups - 1
        df_within  = N - n_valid_groups

        with np.errstate(invalid="ignore", divide="ignore"):
            F = (ssb / df_between) / (ssw / df_within)

        F = np.where(eligible & (df_between > 0) & (df_within > 0), F, np.nan)
        p = np.where(np.isnan(F), np.nan, f.sf(F, df_between, df_within))
        return F, p
    
    def get_stats(self, sample_attribute_tag : str = "att_genotype", fdr : float = 0.05, dropna : bool = True, min_non_nan : int = 2) -> pd.DataFrame:
        """_summary_

        Parameters
        ----------
        sample_attribute_name : str
            _description_
        """
        mapped_sample_index = self._sample_attribute_map
        datatable = self._datatable

        if sample_attribute_tag not in mapped_sample_index.columns:
            sample_attribute_tag = mapped_sample_index.columns[0]

        grouped_samples = mapped_sample_index.groupby(by=sample_attribute_tag)
        grouped_sample_names = [group_data.index for _, group_data in grouped_samples]

        use_plain_f_oneway = False

        if dropna and min_non_nan is None:
            datatable = datatable.dropna()
            use_plain_f_oneway = True  # fully complete rows now, no NaNs left
        elif dropna and min_non_nan is not None:
            datatable = datatable.dropna(thresh=min_non_nan)
        # else: dropna is False -> no filtering, datatable keeps all NaNs

        if datatable.empty:
            raise ValueError("Nan filtering resulted in an empty datatable.")

        data_for_test = [datatable.loc[:, cols].values for cols in grouped_sample_names]
        print("HERE?")
        if use_plain_f_oneway:
            F, p = f_oneway(*data_for_test, axis=1)
        else:
            print(
                "ANOVA:",
                "rows=", len(datatable),
                "groups=", len(grouped_sample_names),
                "shapes=", [x.shape for x in data_for_test],
            )
            min_valid = min_non_nan if min_non_nan is not None else 1

            counts, valid_group = self.get_group_validity(
                datatable, grouped_sample_names, min_valid
            )
            print(
                "valid groups per row:",
                np.unique(valid_group.sum(axis=1), return_counts=True)
            )
            F, p = self.nan_f_oneway(data_for_test, counts, valid_group)
        print("here2??")
        stats = pd.DataFrame({"F" : F, "p-value" : p}, columns=["F","p-value"], index = datatable.index)
        stats = stats.dropna(subset=["p-value"])
        if stats.empty : raise ValueError("All caluclated p-values were nan. Not enough samples/valid values?")
        stats.loc[:,"fdr"] = false_discovery_control(stats["p-value"].values)
        stats = stats.loc[stats["fdr"] <= fdr,:] #subset at fdr 
        return stats
       # return pd.DataFrame()
        
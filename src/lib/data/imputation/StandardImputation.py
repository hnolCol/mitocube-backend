from typing import Tuple, List
from pandas.core.api import DataFrame as DataFrame
from lib.data.imputation.ABCImputation import DatasetImputation

import pandas as pd 
import numpy as np 

class StandardImputation(DatasetImputation):
    """
    Imputes data by first filtering for full quantification in at least on
    samples attribute. Then replaces the missing data. 
    """
   
    def get_imputation(self, 
                       sample_attribute_tag : str, 
                       within_attribute_tag : str = None, 
                       within_attribute_value_tag : List[str] = None, 
                       downshift : float = 1.8, 
                       width : float = 0.3, 
                       nan_threshold : float = 1.0,
                       subset_attribute_value_tags : List[str] = None) -> Tuple[DataFrame, DataFrame]:
        """Imputation is used to mimic the detection limit of the analyzer using 
        a downshifted normal distribution to make data accessible for statistical tests such 
        as t-test and ANOVA. Notably, imputation might introduce a bias. In cases, 
        where a specific sample within a group have less quantified features, the imputation might introduce
        a lot of variance. 

        Parameters
        ----------
        sample_attribute_tag : str
           The attribute tag for which the nan threshold should be checked. 
        within_attribute_tag : str, optional
            An attribute tag for the within group, by default None
        within_attribute_value_tag : str, optional
            A attribute value tag to consider for the imputation. , by default None
        downshift : float, optional
            The downshift of the gaussian distribution from the sample distribution in standard 
            deviations. A value of 1.8 means that the gaussian distribution is create around the sample
            median minus 1.8 times the standard dev (std) of the sample values., by default 1.8
        width : float, optional
            The fraction of the standard deviation to be used to create random data, by default 0.3
        nan_threshold : float, optional
            The fraction of non nan values. A value of 1.0 means that in at least on group (defined by the
            sample attribute and the sample attribute tag) must have quantitative values in all assigned samples , by default 1.0
        subset_attribute_value_tags : List[str], optional
            _description_, by default None

        Returns
        -------
        Tuple[DataFrame, DataFrame]
            _description_

        Raises
        ------
        ValueError
            _description_
        ValueError
            _description_
        ValueError
            _description_
        """
        if not self._dataset.hasData(): raise ValueError("The dataset does not have data yet.")
        
        datatable : pd.DataFrame = self._dataset.getDataTable()
        mapped_sample_names, sample_attrs = self._dataset.getSamplesAttributes()
        if sample_attribute_tag not in mapped_sample_names: raise ValueError("The sample attribute is not found in the dataset metadata.")    

        #if within_attribute_tag is not None and 
        if within_attribute_value_tag is not None and within_attribute_value_tag is not None:
            for within_attr_tag, within_attr_value_tag in zip(within_attribute_tag,within_attribute_value_tag):
                if within_attr_tag not in mapped_sample_names: raise ValueError("Within sample attribute tag not found in the dataset metadata")
                bool_within = mapped_sample_names.loc[:,within_attr_tag] == within_attr_value_tag
                mapped_sample_names = mapped_sample_names.loc[bool_within]
            
        if subset_attribute_value_tags is not None:
            mapped_sample_names.loc[:,sample_attribute_tag].isin(subset_attribute_value_tags)
        
        datatable = datatable.loc[:,mapped_sample_names.index]
        
        keep_idx = pd.Series(np.full(shape=datatable.index.size, fill_value=False,dtype=bool), index = datatable.index) 
        for _, sample_attr_value_data in mapped_sample_names.groupby(by=sample_attribute_tag,sort=False):

            sample_names = sample_attr_value_data.index 
            valid_data = datatable.loc[~keep_idx,sample_names].dropna(thresh=int(nan_threshold * sample_names.size))
            keep_idx.loc[valid_data.index] = True
                    
        datatable_valid_data = datatable.loc[keep_idx]
        is_na_matrix = datatable_valid_data.isna()
        
        std_dev = datatable.std().values
        scaled_dev = std_dev * width 
        column_median = datatable.median().values - downshift * scaled_dev
        random_data = np.random.normal(column_median, scaled_dev,size=(datatable_valid_data.index.size,datatable.columns.size))
        is_na_vs = is_na_matrix.values
        datatable_valid_data.values[is_na_vs] = random_data[is_na_vs]
        return datatable_valid_data, is_na_matrix
        
        
        
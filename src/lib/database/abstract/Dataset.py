
from __future__ import annotations

from abc import abstractmethod, ABC
from collections import OrderedDict
# from datetime import timedelta
from typing import List, Dict, Optional, Tuple, Literal  # , Any
from deprecated import deprecated
from neo4j import Driver 

import pandas as pd
   
    
class DatasetABC(ABC):
    def __init__(self, *args, **kwargs) -> None:
        ""
    
    @abstractmethod 
    def exists(self, tag : str) -> bool: 
        """If a submission tag is associated with a dataset. 
        Datasets are always submissions, but such submission that 
        have quantitative data available to inspect.

        Parameters
        ----------
        tag : str
            _description_

        Returns
        -------
        bool
            _description_
        """
    
    @abstractmethod
    def insert(self, data_table : pd.DataFrame, tag : str):
        ""
    
    
    @abstractmethod
    def get_datatable(self, tag : str, sample_tags : List[str] = None, annotation_tag : str = None, use_sample_tags: bool = False, level : Literal["protein","precursor"] = "protein") -> pd.DataFrame:
        """Returns the database of a submission 

        Parameters
        ----------
        tag : str
            The submission tag 
        sample_tags : List[str], optional
            The sample tags to include in the datatable. If None, all samples are included, by default None
        annotation_tag : str, optional
            The annotation tag to apply to the datatable, by default None
        use_sample_tags : bool, optional
            If True, the columns will be sample tags instead of sample indices, by default False
        level : Literal["protein","precursor"], optional
            The level of quantification to retrieve. Either "protein" or "precursor", by default "protein"
        Returns
        -------
        pd.DataFrame
            The quantitative matrix of data. 
                - 'index' must be the uniprot id 
                - the columns names will bethe index of the sample. (0,1,2,3,4,...) or sample tags (use_sample_tags = True). If sample_tags are provided, only those samples are included.
        """
    
    
    @abstractmethod
    def is_quantified(self, tag : str, feature_tags : List[str]) -> pd.Series:
        """Checks if the given feature is quantified in the given dataset. 

        Parameters
        ----------
        tag : str
            The dataset tag 
        feature_tags : List[str]
            The feature tags. If a feature does not exist, it is simply ignored. 

        Returns
        -------
        pd.Series
            indexes are feature tags, and values in the series are boolean and
            indicate if the feature was quantified. 
        """
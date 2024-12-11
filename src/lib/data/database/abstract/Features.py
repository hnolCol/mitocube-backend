
from __future__ import annotations

from abc import abstractmethod, ABC
from collections import OrderedDict

from typing import List, Dict, Optional, Tuple, Literal  # , Any
from deprecated import deprecated

import pandas as pd

from config.models.user import UserModel 
from config.models.feature import FeatureNeoModel
from config.models.filter import FilterModel
   
   
   
class FeaturesABC(ABC):
    """
    Features (proteins) can be added only from an uniprot
    reference proteome. An should be added using the insert_uniprot_proteome function. 
    Feature should not be updated for a proteome by the admin. 
    There is a common protein sequence file which can be used to define
    'custom' proteins such as controls. 
    """
    
    # @abstractmethod
    # def correlate_features(self):
    #     ""
    
    @abstractmethod
    def is_quantified(self, tags : List[str]) -> pd.DataFrame:
        """Checks if the proteins given by tags are quantified
        Returns a pandas dataframe with the columns tag (str) and quantified (bool)"""
    
    @abstractmethod
    def count(self, quantified : bool = True) -> int:
        """Counts the number of features

        Parameters
        ----------
        quantified : bool, optional
            wether the protein must have been quantified at least once, by default True

        Returns
        -------
        int
            The number of features
        """
        
    @abstractmethod
    def count_quantifications(self, tags : List[str]) -> pd.DataFrame: 
        """Counts the total number of quantifications
        as well as the number of samples in which the protein 
        could also have been detected (e.g. same genotype).

        Parameters
        ----------
        tag : str
            The feature tag 

        Returns
        -------
        pd.DataFrame
            Counts of the quantification of a particular protein as a
            pandas data frame given the following columns:
                - tag (str) : the feature tag
                - n (int) : The number of samples that quantified the feature 
                - total (int) : The number of total samples that could potentially quantify the sample
                (e.g. samples that are analysed the same proteome.)
                - submissions (List[str]) : Submission tags in which the protein has been quantified. 
        """
        
        
    @abstractmethod
    def exists(self, tag : str) -> bool:
        """
        Checks if the given tag is associated with a feature. 
        Parameters
        ----------
        tag : str
            The feature tag 
            
        Returns
        -------
        bool 
        
        """    
    
    @abstractmethod
    def find(self, search_string : str, proteome_tags : List[str] = None, filter_tags : List[str] = None) -> List[FeatureNeoModel]:
        """Search the feature database by a search string.

        Parameters
        ----------
        search_string : str
            _description_
            
        proteome_tags : List[str], optional
            The proteome ids to search in. If None the search will 
            be performed throughout all available proteomes. If a proteome is 
            given but not in the database, an error will be thrown.

        Returns
        -------
        List[FeatureNeoModel]
            _description_
            
        Exception 
        ---------
        
        ValueError 
            If any of the given proteome_tags does not exist.     
        
        """
    
    @abstractmethod
    def get_data(self, tags : List[str], submission_tags : List[str] = None) -> pd.DataFrame:
        """Returns the data in the database for given features (tags).
        The result can be filtered by providing a list of submission tags. 

        Parameters
        ----------
        tags : List[str]
            The feature tags 
        submission_tags : List[str], optional
            The submission tags which should only be considered, if None all submissions in which
            the protein has been quantified will be considered, default None

        Returns
        -------
        pd.DataFrame
            The data as a pandas data frame with the following columns:
                - tag (str) : Feature tag 
                - value (float) : The quantification value 
                - submission_tag(str) : The submission tag in which the feature has been quantified. 
                - sample_index(int): The sample index 
                - attribute_value_tag (str): The tag that the particular sample is associated with. 
                - attribute_tag (str): The tag associating the sample index with an attribute 
                
                
        Example
        -------
         tag    value submission_tag  sample_index attribute_tag attribute_value_tag
        187  Q9Y3P9  24.0935   LOGtC9tNC13b             5  att_genotype               fTBLi
        188  Q9Y3P9  24.1095   LOGtC9tNC13b             4  att_genotype               fTBLi
        189  Q9Y3P9  24.1565   LOGtC9tNC13b             3  att_genotype               fTBLi
        190  Q9Y3P9  24.0691   LOGtC9tNC13b             2  att_genotype               fTBLi
        191  Q9Y3P9  24.1410   LOGtC9tNC13b             1  att_genotype               fTBLi
        """
        
    @abstractmethod
    def get_avg_abundance(self, tags : List[str], submission_tags : List[str] = None) -> pd.DataFrame:
        """Returns the average abundance in every submission the feature has been quantified. 

        Parameters
        ----------
        tags : List[str]
            List of feature tags 
        submission_tags : List[str], optional
            Submission tags that should be considered (e.g. if a filtering is applied). If None
            all datasets will be considered, by default None

        Returns
        -------
        pd.DataFrame
            The average abundance as a pandas data frame. 
                - tag (str) : feature tag 
                - value (float) : Average abundance 
                - submission_tag (str) : The submission tag the abundance was taken from.
        """
    
    @abstractmethod
    def get_f_value(self, tags: List[str], submission_tags: List[str] = None) -> pd.DataFrame:
        """Parameters
        ----------
        tags : List[str]
            List of feature tags 
        submission_tags : List[str], optional
            Submission tags that should be considered (e.g. if a filtering is applied). If None
            all datasets will be considered, by default None

        Returns
        -------
        pd.DataFrame
            The average abundance as a pandas data frame. 
                - tag (str) : feature tag 
                - F (float) : F-statistics
                - submission_tag (str) : The submission tag the F-stats was taken from.
        """
        
    @abstractmethod
    def get_protein_sequence(self, tags : str) -> List[str]:
        """Returns the protein sequences for the given tags

        Parameters
        ----------
        tags : str
            Feature/protein tags

        Returns
        -------
        List[str]
            Protein sequences in a list.
        """
        
    @abstractmethod
    def get_protein_by_tags(self, tags : List[str], as_data_frame : bool = True) -> List[FeatureNeoModel]|pd.DataFrame:
        """Returns the protein information from the database by a list of tags.

        Parameters
        ----------
        tags : List[str]
            The protein tags
        as_data_frame : bool, optional
            If the data should be returned as a pandas data frame, by default True

        Returns
        -------
        List[FeatureNeoModel]|pd.DataFrame
            if as_data_frame is True, then a pandas data frame is returned, otherwise a list of FeatureModel is returned.
            The dataframe then has the same column names as the FeatureNeModel params.
        """


    @abstractmethod
    def get_proteins_by_view(self, limit : int = 10, filter_tags : List[str] = None) -> List[FeatureNeoModel]:
        """Returns the most viewed proteins in the database 

        Parameters
        ----------
        limit : int, optional
            _description_, by default 10

        Returns
        -------
        List[FeatureNeoModel]
            _description_
        """
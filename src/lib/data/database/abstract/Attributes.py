from __future__ import annotations
import pandas as pd
from abc import abstractmethod, ABC
from collections import OrderedDict
# from datetime import timedelta
from typing import List, Dict, Optional, Tuple, Literal  # , Any
from deprecated import deprecated
from config.enums.states import SubmissionStatesEnums
from config.models.attributes import AttributeModel, AttributeUnitResponseModel, AttributeValueModel, AttributeValuesByDatasetModel

class AttributesABC(ABC):
    """Attributes are used in the app to 
    ensure a controlled vocabulary for sample
    submission and meta data collection.
    
    Attributes can handle multiple inputs by users:
    
    a ) Attributes can have specific attributes values that
    are defined for a specific attributes.
    For example, the attribute att_compound (Chemical Compounds)
    has the values: dmso (DMSO), cccp (CCCP). 
    
    b ) features (proteins) might be used as input values 
    for attributes. (has_feature_value = True). This attribute
    can then exclusively be defined by a feature. 
    
    
    Several attributes have the option to be define by numeric input. 
    For example, a drug treatment might be defined by 
    1) concentration 
    2) time of treatment 
    
    See also
    --------
    
    - AttributeModel and AttributeValueModel
    
    """
    @abstractmethod
    def count(self) -> int:
        """The number of attributes

        Returns
        -------
        int
            The number of attributes in the
            database.
        """
    
    @abstractmethod
    def count_values(self) -> int:
        """The number of attribute values

        Returns
        -------
        int
            The number of attribute values
            in the database 
        """
    
    @abstractmethod
    def get(self, tags : List[str] = ["att_compound","att_protease"]) -> List[AttributeModel]:
        """Finds attributes by their tags. If the tag is not in the 
        database it is simply ignored. 

        Parameters
        ----------
        tags : List[str], optional
            The attribute tags, by default ["att_compound","att_protease"]

        Returns
        -------
        List[AttributeModel]
            The list of attributes associated with the provided tags. Please note
            that if the tag is not found, the attribute is simply ignored.

        Raises
        ------
        Exception
            _description_
        """
        
    def get_attributes_and_values_by_search_string(self, 
                                                   search_string : str, 
                                                   min_state : SubmissionStatesEnums =SubmissionStatesEnums.SUBMITTED, param_name : str = None) -> List[Tuple[AttributeModel,List[AttributeValueModel]]]:
        
    @abstractmethod
    def get_attribute_values_by_dataset_tags(self, 
                                             dataset_tags : List[str], 
                                             attribute_tags : list[str] = None, 
                                             attribute_value_tags : List[str] = None) -> List[AttributeValuesByDatasetModel]:
        """Finds all the attribute values that are assigned to a dataset and returns the number of dataset
        that match each attribute value. This is a convenient function to get the datasets tags that have 
        an attribute value and how many are used, as used in a filtering approach. 

        Parameters
        ----------
        dataset_tags : List[str]
            The list of dataset tags to consider. 
        attribute_tags : list[str], optional
            Subset of attribute tags to consider, if None all the attribute available are considered, by default None
        attribute_value_tags : List[str], optional
            Subset of attribute value tags, by default None

        Returns
        -------
        List[AttributeValuesByDatasetModel]
            The result of the query given by a list of AttributeValuesByDatasetModel with the following 
            properties:
                - attribute_value (AttributeValueModel|FeatureNeoModel) : The attribute Value
                - tags (List[str]) : List of dataset tags that have the attribute value
                - counts (int) : The number of datasets tags, equals len(tags)
        """
        
    @abstractmethod
    def get_mandatory_attributes(self)->List[AttributeModel]:
        """Mandatory attributes that are required to fill in
        at the submission state. 

        Returns
        -------
        List[AttributeModel]
            The required attributes for a submission.

        Raises
        ------
        Exception
            If the database query returns an error. 
        """
        
    @abstractmethod
    def unit(self, tag : str) -> List[AttributeUnitResponseModel]:
        """_summary_

        Parameters
        ----------
        tag : str
            _description_

        Returns
        -------
        Dict
            _description_

        Raises
        ------
        Exception
            _description_
        """
        
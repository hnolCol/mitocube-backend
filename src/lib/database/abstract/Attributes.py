from __future__ import annotations
import pandas as pd
from abc import abstractmethod, ABC
from collections import OrderedDict
# from datetime import timedelta
from typing import List, Dict, Optional, Tuple, Literal  # , Any
from deprecated import deprecated
from config.enums.states import SubmissionStatesEnums
from config.models.attributes import AttributeModel, AttributeUnitResponseModel, AttributeValueModel, AttributeValuesBySubmissionModel, AttributeTreeNode, AttributeTraitResponseModel
from config.models.feature import FeatureNeoModel 

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
    def delete(self, tag : str) -> bool:
        """Deletes an attribute and its attribute values by its attribute tag. 
        If an attribute is deleted, all associated values should also be deleted. 
        
        Please note that deleting attributes might lead to submissions that are not
        defined anymore. Assume a sample is described by an attribute and it is deleted. 
        
        Hence, this function should not be used regularly.

        Parameters
        ----------
        tag : str
            The attribute or attribute_value tag. 

        Returns
        -------
        bool
            If the deletion was executed successfully 
        """
        
        
    @abstractmethod
    def delete_value(self, tag : str) -> bool:
        """Deletes a specific attribute value by its tag (attribute value tag)"""    
    
        
    @abstractmethod 
    def exists(self, tag : str = None, trait : str = None) -> bool:
        """Checks if an attribute or attribute value exists by its tag. 

        Parameters
        ----------
        tag : str, default None
            The attribute tag.
        value : str, default None
            The attribute value tag. 
        Returns
        -------
        bool
            _description_
            
        Raises
        ------
        ValueError if tag and value are both None 
        """
           
    
    
    @abstractmethod
    def get(self, 
        tags : List[str] = None, 
        attribute_groups : List[Literal['dataset', 'filter', 'genotype', 'mandatory', 'qc', 'sample', 'user']] = None, 
        group_by : Literal["attribute_group"] = None,
        min_state : SubmissionStatesEnums =SubmissionStatesEnums.SUBMITTED) -> List[str]:
        """Returns attributes by their tags. If the tag is not in the 
        database it is simply ignored. 

        Parameters
        ----------
        tags : List[str], optional
            The attribute tags, by default None (all attributes returned)
        attribute_group : Literal['dataset', 'filter', 'genotype', 'mandatory', 'qc', 'sample', 'user'] 
            Attribute group. If given, only attributes of the specified group is returned.
        Returns
        -------
        List[str]
            The list of attributes associated with the provided tags. Please note
            that if the tag is not found, the attribute is simply ignored.
            If tags is None, all attributes are returned. 

        Raises
        ------
        Exception
            _description_
        """
        
    @abstractmethod  
    def get_values(self, tags : List[str]) -> List[AttributeValueModel|FeatureNeoModel]:
        """Returns the attribute values given by a tag. 
        If a tag is not found in the database, it is simply ignored.

        Parameters
        ----------
        tags : List[str]
            _description_

        Returns
        -------
        List[AttributeValueModel|FeatureNeoModel]
            _description_
        """
        
    @abstractmethod
    def get_attribute_group_tags(self, limit : int = None) -> List[str]:
        """Returns the attribute group tags present in the database."""
        
    @abstractmethod
    def get_attribute_hierarchy(self, tags : List[str], submission_tag : str) -> List[AttributeTreeNode]:
        """Returns the hierarchy of the attributes, that 
        match the given tags. 

        Parameters
        ----------
        tags : List[str]
            The attribute tags to get the hierarchy for. 
            
        Returns
        --------
        List[AttributeTreeNode]
            The hierarchy as given such as a list of keys
                - tag 
                - IS_PARENT_OF 
            
            
        """
        
    @abstractmethod
    def get_values_by_submission_tag(self, submission_tag : str, tags : List[str] = None) -> List[AttributeValueModel]:
        ""
        
        
    # @abstractmethod
    # def get_attributes_and_values_for_submission(self, submission_tag : str) -> AttributeResponseModel:
    #     """Returns the attribute/value properties and values that are associated with a 
    #     submission tag. This includes dataset as well as sample attributes. The attributes should be sorted by
    #     the attribute priority and the min_state properties.

    #     Parameters
    #     ----------
    #     submission_tag : str
    #         The submission tag

    #     Returns
    #     -------
    #     Dict[]
    #         _description_
    #     """
        
    @abstractmethod    
    def get_attributes_by_search_string(self, 
                                                   search_string : str, 
                                                   min_state : SubmissionStatesEnums = SubmissionStatesEnums.SUBMITTED, 
                                                   limit : int = None,
                                                   param_name : Literal["allow_for_dataset",
                                                                        "mandatory_for_submission",
                                                                        "allow_as_filter",
                                                                        "allow_for_genotype",
                                                                        "allow_for_measurement",
                                                                        "allow_for_qc",
                                                                        "mandatory_for_active"] = None) -> List[Tuple[AttributeModel,List[AttributeValueModel]]]:
        ""
    
    @abstractmethod    
    def find_attributes_and_traits(self, 
                                                   search_string : str = None, 
                                                   min_state : SubmissionStatesEnums = SubmissionStatesEnums.SUBMITTED, 
                                                   limit : int = None,
                                                   attribute_groups : Literal['dataset', 'filter', 'genotype', 'mandatory', 'qc', 'sample', 'user'] = None
                                                    ) -> List[AttributeTraitResponseModel]:
        """Finds attributes and attribute values by a search string the minimal required 
        state as well as a boolean param can be set. 
        TODO: Rename to find? 

        Parameters
        ----------
        search_string : str
            The search string to find an attribute. 
        min_state : SubmissionStatesEnums, optional
            The minimal state of a submission/dataset that is required. Certain attribute can only be 
            selected if the submission is in specific state. For example, you can only set the 
            mass spectrometer if the samples are being measured, by default SubmissionStatesEnums.SUBMITTED
        limit : int, optional
            The maximum of attributes to return

        Returns
        -------
        List[Tuple[AttributeModel,List[AttributeValueModel]]]
            If an attribute value matches the search string, the attribute must always be returned. 
        """

    
    
    @abstractmethod
    def get_attribute_values_by_dataset_tags(self, 
                                             dataset_tags : List[str], 
                                             attribute_tags : list[str] = None, 
                                             attribute_value_tags : List[str] = None) -> List[AttributeValuesBySubmissionModel]:
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
        List[AttributeValuesBySubmissionModel]
            The result of the query given by a list of AttributeValuesBySubmissionModel with the following 
            properties:
                - attribute_value (AttributeValueModel|FeatureNeoModel) : The attribute Value
                - tags (List[str]) : List of dataset tags that have the attribute value
                - counts (int) : The number of datasets tags, equals len(tags)
        """
    @abstractmethod
    def get_min_state(self, tag : str) -> SubmissionStatesEnums:
        """Returns the minimum state for the given attribute tag."""
    
    @abstractmethod
    def get_priority(self, tag : str) -> int:
        """Returns the priority of the attribute with the given tag."""
        
    @abstractmethod
    def get_mandatory_attributes(self, state : SubmissionStatesEnums = None)->List[AttributeModel]:
        """Mandatory attributes that are required to fill in
        at the submission state. 

        Parameters
        ----------
        state 
            Return mandatory attributes for the given state only. 


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
    def get_attributes_for_user(self) -> List[AttributeModel]:
        "Returns the attributes that can be used for the user."
        
    @abstractmethod
    def find_attribute(self, search_string : str, 
                       attribute_group : Literal['dataset', 'filter', 'genotype', 'mandatory', 'qc', 'sample', 'user'] = None, 
                       min_state : SubmissionStatesEnums = None,
                       limit : int = 20,
                       group_by : Literal["attribute_group"] = None) -> List[str]|Dict[str, List[str]]:
        "Finds attribute tags"
    
    @abstractmethod
    def find_trait(self, search_string : str, attribute_tag : str = None, limit : int = None) -> List[str]:
        """Finds a trait tag by a search string. The search space might be limited by defining an attribute_tag (e.g. 
        only traits of the attribute can be found.)

        Parameters
        ----------
        search_string : str
            The search string matching th tag or the description. 
        attribute_tag : str, optional
            _description_, by default None
        limit : int, optional
            _description_, by default None

        Returns
        -------
        List[str]
            Matching traits tags. 
        """
         
         
        
    @abstractmethod
    def get_children(self, tag : str) -> List[str]:
        "Returns a list of children attribute tags. If no children define, an empty list is returned."
        
    @abstractmethod
    def get_trait_tags(self, tag : str = None, limit : int = None) ->  List[AttributeValueModel]:
        "Return the trait_tags for a given attribute_tag"
        
    @abstractmethod
    def get_trait_text(self, tag : str) -> str:
        "Returns the text associated with a trait tag. If not found, an empty string is returned."
        
    @abstractmethod
    def count_traits(self, tag : str) -> int:
        """Returns the number of traits for a single attribute tag"""
        
    @abstractmethod
    def insert(self, attribute : AttributeModel, attribute_values : List[AttributeValueModel] = None) -> bool:
        """Inserts an attribute and corresponding attribute_values to the database. 
        

        Parameters
        ----------
        attribute : AttributeModel
            The attribute that should be inserted. 
        attribute_values : List[AttributeValueModel]
            The corresponding attribute_values. 

        Returns
        -------
        bool
            If the insertion was successful. 
            
        Exception
        ---------
        ValueError
            If the attribute allows features (has_feature_values = True), but attribute_values
            are provided which is not allowed.
        ValueError
            If the attribute_tag is already in the database. 
        """
        
    @abstractmethod 
    def insert_value(self, tag : str, attribute_value : AttributeValueModel) -> bool:
        "insert value for a given attribute"
       
        
    
        
    @abstractmethod
    def update(self, attribute : AttributeModel, attribute_values : List[AttributeValueModel] = None) -> bool:
        """Updates an attribute and its values. 

        Parameters
        ----------
        attribute : AttributeModel
            _description_
        attribute_values : List[AttributeValueModel], optional
            _description_, by default None

        Returns
        -------
        bool
            _description_
        """
        
    @abstractmethod
    def update_values(self, attribute : AttributeModel, attribute_values : List[AttributeValueModel], join : bool = True) -> bool:
        """Updates the values of an attribute

        Parameters
        ----------
        attribute : AttributeModel
            The attribute for which the values should be updated. 
        attribute_values : List[AttributeValueModel]
            The updated attribute_values. 
        join : bool 
            Specify if the attribute values should be joined to the others (True) or replaced (False). 
            The union of the attribute values is added. 
            
        Returns
        -------
        bool
            _description_
        """
    
    
    @abstractmethod
    def get_unittype(self, tags : List[str]) -> Dict[str,List[str]]:
        """Returns the unittype(s) by an attribute tag list. 
        A UnitType is for example 'Concentration'. For example 
        a chemical component might have the UnitType 'concentration' and
        'time'. To define the duration of the treatment and the used concentration. 
        Each UnitType has several pre define Units (mg/ml, M, %). 
        Of note, 'Features' are also considered as a UnitType and allow to define 
        a specific feature to an attribute. 
        
        Parameters
        ----------
        tags : List[str]
            List of attribute tags to get the UnitType for. 
            
        Returns 
        -------
        Dict[str,List[str]]
            Key are the attribute tags 
            and the List (values) contains the tags of the unittypes 

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
        List[AttributeUnitResponseModel]
            _description_

        Raises
        ------
        Exception
            _description_
        """
        
        
    @abstractmethod
    def values(self, tags : List[str]) -> List[AttributeValueModel| FeatureNeoModel]:
        """Returns the attribute values given by their tags.
        If a tag is not present in the database, it is simply ignored. 

        Parameters
        ----------
        tags : List[str]
            The list of attribute values

        Returns
        -------
        [AttributeValueModel|FeatureNeoModel]
            The list of attribute values / features. 
        """
from abc import abstractmethod, ABC 
from typing import List, Dict, Literal
import pandas as pd 
from config.models.conditions_applications import ConditionApplicationAttributeModel
from config.models.samples import SampleModel
from config.models.attributes import AttributeTree
from config.models.calculations.quantile import QuantileModel

class SamplesABC(ABC):
    def __init__(self) -> None:
        ""
        
    @abstractmethod
    def count(self,
              has_protein_quantification : bool = False, 
              has_peptide_quantification : bool = False, 
              protein_group_tag : str = None, 
              trait_tag : str = None, 
              submission_tag : str = None,
              instrument_tag : str = None,
              genotype_tag : str = None) -> int:
        
        """Counts the number of samples. The filters are optional. However no combination is supported.
        If protein_group_tag is provided, only samples that have quantified the given protein group are counted, but the 
        submission_tag and trait_tag filters are ignored. The quantification filters are applied in any case.+.
        
        Parameters
        ----------  
        has_protein_quantification : bool, optional
            If True, only counts samples that have at least one quantified feature are counted
        has_peptide_quantification : bool, optional
            If True, only counts samples that have at least one quantified peptide are counted
        protein_group_tag : str, optional
            If provided, only counts samples that have quantified the given protein group.
        submission_tag : str, optional
            If provided, only counts samples that are part of the given submission.
        trait_tag : str, optional
            If provided, only counts samples that have the given trait. 
        instrument_tag : str, optional
            If provided, only counts samples that were measured by the given instrument.
        Returns 
        -------
        int
            The number of samples matching the criteria.
        """
    @abstractmethod
    def count_quantified_protein_groups(self, tag : str, submission_tag : str) -> List[Dict]:
        """Counts the number of quantified protein groups for a given sample.

        Parameters
        ----------
        tag : str
            The tag of the sample.
        submission_tag : str
            The tag of the submission.

        Returns
        -------
        int
            The number of quantified protein groups for the given sample.
        """
    @abstractmethod
    def calculate_test_quantification_distribution(self, submission_tag : str, testParam : Dict, quantification_type : Literal["protein_groups","precursors"], annotation_tag : str = None) -> QuantileModel:
        """Calculates the quantification distribution for a given submission and quantification type based on a statistical test. This is used to calculate the distribution for the test results in the volcano plot."""
        
        
    @abstractmethod
    def get(self, tag : str) -> SampleModel:
        "Returns the sample information for a given sample tag."
        
    @abstractmethod
    def exists(self, tag : str) -> bool: 
        """Checks if a tag is associated with sample 

        Parameters
        ----------
        tag : str
            The sample run tag 

        Returns
        -------
        bool
            If the given tag is associated with a sample. 
        """
    
    @abstractmethod
    def insert(self, submission_tag : str, sample_name : str, sample_index : int, replicate: int = None, return_tag_if_exists : bool = False, connect_if_exists : bool = False) -> str:
        """Inserts a sample into the database.
        The tag will be generated automatically as a random UUID.
        Parameters
        ----------
        submission_tag : str
            The submission tag associated with the sample.
        sample_name : str
            The name of the sample.
        sample_index : int
            The index of the sample in the submission.
        return_tag_if_exists : bool, optional
            If True, returns the existing sample tag if the sample already exists. If False, raises an error if the sample exists.
        connect_if_exists : bool, optional
            If True and return_tag_if_exists is True, connects the existing sample to the submission if it is not already connected. Ignored if return_tag_if_exists is False.
        Returns
        -------
        str
            The generated sample tag.
        """
        
    
    @abstractmethod
    def get_sample(tag : str) -> SampleModel:
        ""
    @abstractmethod
    def get_sample_tag_by_index_and_submission(self, sample_index : int, submission_tag : str) -> List[str]:
        "Returns a sample an its trait as well genotype annotation."
        
    @abstractmethod
    def get_condition_applications(self, tag: str, attribute_tags : List[str] = None, group_by_attribute : bool = False) -> List[str]|List[ConditionApplicationAttributeModel]:
        """Get all condition procedures for a given sample. 
        
        Parameters
        ----------
        tag : str
            The tag of the sample to get the condition procedures for.
        attribute_tags : List[str], optional
            If provided, only condition procedures with the given attribute tags are returned. By default, None, which means that condition procedures of all attributes are returned.
        group_by_attribute : bool, optional
            If True, the results are grouped by attribute and returned as a list of ConditionApplicationAttribute
            
        Returns
        -------
        List[str]|List[ConditionApplicationAttributeModel]
            A list of condition procedure tags.
            If group_by_attribute is True, a list of ConditionApplicationAttributeModel is returned.
        """
        
    @abstractmethod
    def get_condition_applications_by_sample_for_submission(self, submission_tag : str, join : str = ";", pivot : bool = True, sort_ca_tags : bool = True, return_sample_index : bool = True) -> pd.DataFrame:
        """Get all condition procedures for all samples in a submission, indexed by sample index. 
        
        Parameters
        ----------
        submission_tag : str
            The submission tag to get the condition procedures for.
        join : str, optional
            The string to join multiple condition procedure tags, by default ";"
        pivot : bool, optional
            If True, the results are pivoted to have attributes as columns, by default True
        sort_ca_tags : bool, optional
            If True, the condition application tags for each attribute are sorted alphabetically before joining., by default True   
        return_sample_index : bool, optional
            If True, the DataFrame will be indexed by sample index. If False, it will be indexed by sample tag.
        Returns
        -------
        pd.DataFrame
            A DataFrame with sample indices as index and condition procedures as columns.
            The columns names represent the instance attribute (e.g. att_environment).
            The values are the condition procedure tags. 
            Multiple tags are separated by a semicolon.
        """
        pass
    
    @abstractmethod
    def get_genotypes_by_sample_for_submission(self, submission_tag : str, join : str = ";", pivot : bool = True, sort_ca_tags : bool = True, return_sample_index : bool = True) -> pd.DataFrame:
        """Get all genotypes for all samples in a submission, indexed by sample index."""


    @abstractmethod
    def get_quantified_data_for_feature(self, tag : str, feature_tag : str, metrics : Literal["raw","z_score_sample","z_score_protein_group","log2_fc_vs_mean"] = "raw") -> float|None: 
        """Get the quantified data for a given sample and feature.
        A feature may be protein group or peptide. Returns None if no data is found.
        """
        pass

    @abstractmethod
    def get_sample_genotype(self, tag : str) -> List[str]:
        """Get the genotype tag for a given sample
        """
        pass

    @abstractmethod
    def insert_proteins(self, submission_tag: str, sample_name: str, protein_tags: List[str]):
        """Inserts proteins for a given sample in a submission.

        Parameters
        ----------
        submission_tag : str
            The submission tag.
        sample_name : str
            The sample name.
        protein_tags : List[str]
            The list of protein tags to insert.

        Returns
        -------
        bool
            True if the insertion was successful, False otherwise.
        """

    @abstractmethod
    def update( self, tag: str, text: str = None, genotype_tag: str = None, condition_applications: List[AttributeTree] = None) -> bool:
        """Update the sample information for a given sample tag.    
        """


    @abstractmethod
    def insert_genotype(self, sample_tags: List[str], genotype_tag: str) -> bool:
        """Set the genotype for a given sample.

        Parameters
        ----------
        sample_tags : List[str]
            The tags of the samples to set the genotype for.
        genotype_tag : str
            The tag of the genotype to set for the samples.

        Returns
        -------
        bool
            True if the update was successful, False otherwise.
        """

    @abstractmethod
    def is_excluded(self, tag: str) -> bool:
        """Checks whether a sample is excluded from statistical analysis."""

    @abstractmethod
    def get_replicate(self, tag: str) -> int:
        """Get the replicate number for a given sample.

        Parameters
        ----------
        tag : str
            The tag of the sample to get the replicate number for.

        Returns
        -------
        int
            The replicate number for the given sample.
        """        

    @abstractmethod
    def set_replicate(self, tag: str, replicate: int) -> bool:
        """Set the replicate number for a given sample.

        Parameters
        ----------
        tag : str
            The tag of the sample to set the replicate number for.
        replicate : int
            The replicate number to set for the sample.

        Returns
        -------
        bool
            True if the update was successful, False otherwise.
        """
    
    @abstractmethod
    def get_sample_list(self, submission_tag: str) -> pd.DataFrame:
        """Returns a DataFrame ready for RunListCreator.
        Index = sample names (s.text), columns = attribute tags, values = condition application tag strings."""


    @abstractmethod
    def set_excluded(self, tag: str, excluded: bool) -> bool:
        "Sets whether a sample is excluded from statistical analysis / quantification aggregation."
    
    @abstractmethod
    def has_quantification_distributution(self, tag : str, quantification_type : Literal["protein_groups","precursors"], annotation_tag : str = None) -> bool:
        """Checks if a quantification distribution exists for a given sample and quantification type."""
        
    @abstractmethod
    def get_quantification_distribution(self, tag : str, quantification_type : Literal["protein_groups","precursors"], annotation_tag : str = None) -> QuantileModel:
        """Returns the distribution of quantification values for a given sample and quantification type. The distribution is represented as a QuantileModel instance."""

        

    @abstractmethod
    def insert_quantification_distribution(self, submission_tag : str, quantification_type : Literal["protein_groups","precursors"], distribution : QuantileModel, annotation_tag : str = None) -> bool:
        """Inserts the quantification distribution for a given submission and quantification type. This can be used to store pre-calculated distributions for faster retrieval."""
        
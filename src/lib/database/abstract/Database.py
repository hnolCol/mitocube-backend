from __future__ import annotations

from abc import abstractmethod, ABC
from collections import OrderedDict
# from datetime import timedelta
from typing import List, Dict, Optional, Tuple, Literal  # , Any
from deprecated import deprecated
from neo4j import Driver 

import pandas as pd

from lib.database.abstract.Attributes import AttributesABC
from lib.database.abstract.Filter import FilterABC
from lib.database.abstract.Users import UserABC 
from lib.database.abstract.Meta import MetaABC 
from lib.database.abstract.Submission import SubmissionFilterABC, SubmissionsABC, SubmissionSummaryABC
from lib.database.abstract.Features import FeaturesABC
from lib.database.abstract.Dataset import DatasetABC
from lib.database.abstract.Genotypes import GenotypeABC
from lib.database.abstract.Peptides import PeptidesABC
from lib.database.abstract.QC import QCABC
from lib.database.abstract.Instruments import InstrumentsABC, InstrumentStatesABC
from lib.database.abstract.Timeline import TimelineABC 
from lib.database.abstract.ResearchGroup import ResearchGroupABC
from lib.database.abstract.Phenotypes import PhenotypeABC
from lib.database.abstract.Maintenance import MaintenanceProcedureABC, MaintenanceEventABC, ExternalServicesABC
from lib.database.abstract.SpareParts import SparePartsABC
from lib.database.abstract.Symptoms import SymptomABC
from lib.database.abstract.Samples import SamplesABC
from lib.database.abstract.ConditionApplications import ConditionApplicationABC
from lib.database.abstract.Metatext import MetaTextABC
from lib.database.abstract.News import NewsABC
from lib.database.abstract.OpenAi import OpenAIClient
from lib.database.abstract.Cache import CacheABC
from lib.database.abstract.ProteinGroups import ProteinGroupsABC
from lib.database.abstract.Proteins import ProteinsABC
from lib.database.abstract.Proteomes import ProteomesABC
from lib.database.abstract.Diseases import DiseaseABC
from lib.database.abstract.Variants import VariantABC
from lib.database.abstract.PhenotypeAssociation import PhenotypeAssociationABC
from config.settings.db import get_db_settings
from config.models.submissions.submissions import DatasetSubmissionModel
from lib.database.abstract.Annotations import AnnotationsABC, AnnotationGroupsABC
from lib.database.abstract.Crosslink import CrosslinkABC
from lib.database.abstract.external_resource import ExternalResourceABC



DB_SETTINGS = get_db_settings()

## load database 

class DatabaseABC(ABC):
    """
    Main Database Class. 
    
    More specific interfaces are available
    
    - attributes 
        Handles the attributes (controlled vocabulary)
    - user
        User database, handles authorization, sign in etc 
    - submission_filter 
        Filtering submissions using various meta data input such 
        as attributes, attribute values, users, features etc 
    - filters 
        Sets of features that can be used to quickly filter a 
        set of proteins (example: MitoCarta 3.0)
    """
    
    
    meta : MetaABC = None 
    users : UserABC = None 
    features : FeaturesABC = None
    attributes : AttributesABC = None
    filters : FilterABC = None
    submissions : SubmissionsABC = None
    submission_filter : SubmissionFilterABC = None
    datasets : DatasetABC = None 
    genotypes : GenotypeABC = None
    qc : QCABC = None 
    peptides : PeptidesABC = None 
    protein_groups : ProteinGroupsABC = None 
    submission_summary : SubmissionSummaryABC = None
    instruments : InstrumentsABC = None
    instrument_states : InstrumentStatesABC = None
    timeline : TimelineABC = None 
    research_groups : ResearchGroupABC = None
    phenotypes: PhenotypeABC = None
    maintenance_procedures : MaintenanceProcedureABC  = None 
    maintenance_events : MaintenanceEventABC = None
    external_service : ExternalServicesABC = None
    spareparts : SparePartsABC = None
    symptoms : SymptomABC = None
    samples : SamplesABC = None
    condition_applications : ConditionApplicationABC = None
    metatexts : MetaTextABC = None
    news : NewsABC = None
    openai : OpenAIClient  = None #not checked for existence, since it is not mandatory
    cache : CacheABC = None 
    proteins :  ProteinsABC = None
    annotations : AnnotationsABC = None
    annotation_groups : AnnotationGroupsABC = None
    proteomes : ProteomesABC = None
    diseases : DiseaseABC = None
    variants : VariantABC = None
    phenotype_associations : PhenotypeAssociationABC = None
    crosslinks : CrosslinkABC = None
    external_resources : ExternalResourceABC = None

    def __init__(self):
        """The abstract database class that defines
        all the required methods as abstractmethod in order
        to make the backend function. You can use this as a guideline 
        to implement your own database class. 
        
        Class Attributes
        ----------
        Attributes
            Sub database classes:
            
                - 'meta' (MetaABC) : Metadata class. 
                - 'user' (UserABC) : User class which handles user verification, addition and blocking. 
                - 'attributes' (AttributesABC) : Attribute database class to manage attributes.
                - 'filters' (FilterABC) : Set of proteins that can be used for filtering. 
                - 'submission_filter' (SubmissionFilterABC) : Filtering class for submission to quickly find 
                    submission that match specific criteria (attribute_values, proteomes, users)
        Raises
        ------
        NotImplementedError
            If an class attribute is missing. 
        TypeError
            If an  class attribute is not of the correct type. 
        """
        if self.meta is None:
            raise NotImplementedError("A database class must have the meta attribute defined.")
        
        if not isinstance(self.meta, MetaABC):
            raise TypeError("The attribute meta must be an instance of MetaABC")
        
        if self.users is None:
            raise NotImplementedError("A database class must have the users attribute defined.")
        
        if not isinstance(self.users, UserABC):
            raise TypeError("The attribute user must be an instance of UserABC")
    
        if self.attributes is None:
            raise NotImplementedError("A database class must have the attributes class attribute defined.")
        
        if not isinstance(self.attributes, AttributesABC):
            raise TypeError("The attribute user must be an instance of AttributesABC")
        
        if self.filters is None:
            raise NotImplementedError("A database class must have the filter attribute defined.")
        
        if not isinstance(self.filters, FilterABC):
            raise TypeError("The attribute filters must be an instance of FilterABC")
        
        if self.submission_filter is None:
            raise NotImplementedError("A database class must have the submission_filter attribute defined.")
        
        if not isinstance(self.submission_filter,SubmissionFilterABC):
            raise TypeError("The submission_filter class must be an instance of SubmissionFilterABC")
        
        if self.submissions is None:
            raise NotImplementedError("A database class must have the submissions attribute defined.")
        
        if not isinstance(self.submissions, SubmissionsABC):
            raise TypeError("The submissions class must be an instance of SubmissionABC")
        
        if self.datasets is None:
            raise NotImplementedError("A database class must have the submissions attribute defined.")
        
        if not isinstance(self.datasets, DatasetABC):
            raise TypeError("The datasets class must be an instance of DatasetABC")
        
        if self.genotypes is None:
            raise NotImplementedError("A database class must have the genotypes attribute defined")
        if not isinstance(self.genotypes,GenotypeABC):
            raise TypeError("The genotypes class must be an instance of GenotypeABC")

        if self.qc is None:
            raise NotImplementedError("A database class must have the qc attribute defined")
        if not isinstance(self.qc,QCABC):
            raise TypeError("The qc class must be an instance of QCABC")    
        
        if self.peptides is None:
            raise NotImplementedError("A database class must have the peptides attribute defined")
        
        if not isinstance(self.peptides,PeptidesABC):
            raise TypeError("The peptides class must be an instance of PeptidesABC")   
         
        if self.instruments is None:
            raise  NotImplementedError("A database class must have the instrument attribute defined")
        
        if not isinstance(self.instruments,InstrumentsABC):
            raise TypeError("The instruments class must be an instance of InstrumentABC")    
        
        if self.instrument_states is None:
            raise  NotImplementedError("A database class must have the instrument_states attribute defined")
        
        if not isinstance(self.instrument_states,InstrumentStatesABC):
            raise TypeError("The instrument_states class must be an instance of InstrumentStatesABC")    
        
        if self.timeline is None:
            raise NotImplementedError("A database class must have the timeline attribute defined.")
        
        if not isinstance(self.timeline, TimelineABC):
            raise TypeError("The timeline class must be an instance of the TimelineABC.")
        
        if self.research_groups is None:
            raise NotImplementedError("A database class must have the timeline attribute defined.")
        if not isinstance(self.research_groups,ResearchGroupABC):
            raise TypeError("The research_groups class must be an instance of the ResearchGroupABC.")
        
        if self.phenotypes is None:
            raise NotImplementedError("A database class must have the phenotype attribute defined.")
        if not isinstance(self.phenotypes,PhenotypeABC):
            raise TypeError("The phenotype class must be an instance of the PhenotypeABC.")
        
        if self.maintenance_procedures is None:
            raise NotImplementedError("A database class must have the maintenance attribute defined.")
        if not isinstance(self.maintenance_procedures, MaintenanceProcedureABC):
            raise TypeError("The phenotype class must be an instance of the MaintenanceProcedureABC.")
        if self.samples is None:
            raise NotImplementedError("A database class must have the samples attribute defined.")
        if not isinstance(self.samples, SamplesABC):
            raise TypeError("The samples class must be an instance of the SamplesABC.")

        if self.condition_applications is None:
            raise NotImplementedError("A database class must have the condition_applications attribute defined.")
        if not isinstance(self.condition_applications, ConditionApplicationABC):
            raise TypeError("The condition_applications class must be an instance of the ConditionApplicationABC.")

        if self.news is None:
            raise NotImplementedError("A database class must have the news attribute defined.")
        if not isinstance(self.news, NewsABC):
            raise TypeError("The news class must be an instance of the NewsABC.")
        
        if self.metatexts is None:
            raise NotImplementedError("A database class must have the metatexts attribute defined.")
        if not isinstance(self.metatexts, MetaTextABC):     
            raise TypeError("The metatexts class must be an instance of the MetaTextABC.")
        
        if self.cache is None:
            raise NotImplementedError("A database class must have the cache attribute defined.")
        if not isinstance(self.cache, CacheABC):
            raise TypeError("The cache class must be an instance of the CacheABC.")
        
        if self.protein_groups is None:
            raise NotImplementedError("A database class must have the protein_groups attribute defined.")
        if not isinstance(self.protein_groups, ProteinGroupsABC):
            raise TypeError("The protein_groups class must be an instance of the ProteinGroupsABC.")

        if self.proteins is None:
            raise NotImplementedError("A database class must have the proteins attribute defined.")
        if not isinstance(self.proteins, ProteinsABC):
            raise TypeError("The proteins class must be an instance of the ProteinsABC.")




    def submission_exists(self, tag : str) -> bool:
        """Checks if the tag is associated with a dataset. 
        Use this function to check if a tag exists. 

        Parameters
        ----------
        tag : str
            The dataset/submission tag. 

        Returns
        -------
        bool
            If the tag is associated with a dataset/submission.
        """
        
        return self.submissions.exists(tag = tag)
    
    def submission_has_dataset(self, tag : str) -> bool:
        """Checks if a submission exists and if quantitative 
        data are associated with it. Note, that tags that are not 
        found, are simply ignored and False is returned.

        Parameters
        ----------
        tag : str
            The submission tag 

        Returns
        -------
        bool
            If quantitative data are available for the submission.
        """
        return self.datasets.exists(tag)
        
    def get_submission_tags(self, limit : int = None) -> List[str]:
        ""
        return self.submission_filter.get_all_tags(limit = limit)
    
    @abstractmethod
    def get_feature_data(self, tag : str) -> List[Dict]:
        """Returns the feature (protein) data
        by its tag.

        Parameters
        ----------
        tag : str
            The feature tag 

        Returns
        -------
        List[Dict]
            The data 
            TODO: Define model on how the data should be returned ! 
        """
        
    def get_datatable(self, 
                      tag : str, 
                      annotation_tag : str = None, 
                      sample_tags : List[str] = None,
                      use_sample_tags: bool = False, 
                      level : Literal["protein","precursor"] = "protein") -> pd.DataFrame:
        """Returns the quantitative matrix containing the 
        features as tags (index) an the quant values in wide format
        columns indicate sample indices and rows features. Values in
        the matrix are log2 intensitiees/abundance 

        Parameters
        ----------
        tag : str
            The submission tag.
        annotation_tag : str
            If a tag is given and exists, then the datatable will 
            be filtered by the filter (list of feature tags). 
        sample_tags : List[str], optional
            If a list of sample tags is given, only those samples
            will be included in the datatable, by default None
        use_sample_tags : bool, optional
            If True, the columns will be sample tags instead of sample indices, by default False
        level : Literal["protein","precursor"], optional
            The level of quantification to retrieve. Either "protein" or "precursor", by default "protein"
        Returns
        -------
        pd.DataFrame
            _description_
        """
    
        cache_key = self.cache.calculate_key([tag,annotation_tag if annotation_tag is not None else "", ",".join(sample_tags) if sample_tags is not None and len(sample_tags) > 0 else "", str(use_sample_tags), level])
        if self.cache.exists(cache_key):
            return self.cache.get(cache_key)
        datatable = self.datasets.get_datatable(tag = tag, annotation_tag = annotation_tag, sample_tags = sample_tags, use_sample_tags=use_sample_tags, level=level)
        self.cache.insert(cache_key, datatable)
        return datatable 
        
   
    def get_meta_data(self, tag : str) -> DatasetSubmissionModel:
        ""
        return self.submissions.get(tag = tag)
    
    
    def insert_dataset(self, data_table : pd.DataFrame, tag : str):
        """Adds a dataset to the database. 

        Parameters
        ----------
        data_table : pd.DataFrame
            _description_
        tag : str
            The submission tag. 
        """
        return self.datasets.insert(data_table,tag)
    
    
    def insert_meta(self, meta_data : DatasetSubmissionModel):
        """Insert meta data

        Parameters
        ----------
        meta_data : DatasetSubmissionModel
            The meta data stored as a DatasetSubmissionModel. 

        Returns
        -------
        _type_
            _description_

        Raises
        ------
        Exception
            _description_
        """
        return self.submissions.insert(submission=meta_data)
        
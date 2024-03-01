# from __future__ import annotations

import pandas as pd 
import typing
from typing import List, Dict, Any, Tuple, Optional
from pydantic import BaseModel, Field, field_serializer

from abc import abstractmethod
from deprecated import deprecated
from lib.DesignPatterns import JsonSerializable
from config.settings.db import get_db_settings
from config.models.submissions.submissions import DatasetSubmissionModel
from config.models.submissions.runs import RunListModel
import random
from lib.DesignPatterns import JsonSerializable
from collections import OrderedDict
from services.transforms import value_mapper_from_dict
import time 
import os 

DB_SETTINGS = get_db_settings()

class MCDataset(JsonSerializable):
    """Replacement for the Data.Dataset"""
    # Todo: Write documentation
    def __init__(self,
                 dataset_id: int = -1,
                 label: str = None,
                 state: str = None,
                 title: str = None,
                 user_label : str = None,
                 collaborators : typing.List[str] = [],
                 created_on: str = None,  # ToDo: Check DataType Date
                 uploaded_on: str = None,
                 data_table: pd.DataFrame = None,
                 metatexts: typing.Dict = None,
                 urls: typing.List = None,
                 replicates: typing.List[int] = [],
                 attributes_dataset: typing.Dict = None,
                 attributes_samples: typing.Dict = None,
                 samples_genotypes: typing.Dict = None,
                 sample_names : typing.List[str] = [],
                 timeline : typing.Dict = None,
                 runlist : typing.Optional[RunListModel] = None,
                 loadFromDatabase: bool = False, 
                 load_meta_only : bool = False):  # ToDo: Check DataType Date
        """Constructor"""
        # Todo: Write documentation
        self._id = dataset_id
        self._label = label
        self._load_meta_only = load_meta_only
        self._cached_data_table = None
        self._last_meta_load = None

        if loadFromDatabase:
            self._refresh()
        elif load_meta_only:
            self._read_meta()
        else:
            self._loadedFromDatabase = False

            # self._contact_email = contact_email
            self._state = state

            self._cached_data_table = data_table

            self._metatexts = metatexts
            self._urls = urls
            self._replicates = replicates
            self._attributes_dataset = attributes_dataset
            self._attributes_samples = attributes_samples
            self._sample_names = sample_names
            self._samples_genotypes = samples_genotypes
            #self._instrument = instrument
            self._runlist = runlist
            self._title = title
            self._user_label = user_label
            self._collaborators = collaborators
            self._timeline = timeline
            #self._experimentator = experimentator
            #self._name_group = name_group

            self._created_on = created_on
            self._uploaded_on = uploaded_on

        # ToDo: Add Self stated updated / read date?

    def _check_reload(self) -> bool:
        
        if self._last_meta_load  is None :
            return True
        path_dataset = os.path.join(DB_SETTINGS.db_datadir,self._label) # TO DO: CHange this, 
        path_meta = os.path.join(path_dataset,"params.json")
        if os.path.exists(path_meta):
            reload_file = os.stat(path_meta).st_mtime >= self._last_meta_load
            return reload_file
        return False 

    def _isMetaLoaded(self) -> bool:
        ""
        return self._state is not None 
        
    def _isDataTableLoaded(self) -> bool:
        "" 
        return self._cached_data_table is not None
        
    def _isLoaded(self) -> bool:
        """"""
        # Todo: Write documentation
        #data table is not required as a dataset can also only load meta data? 
        return  self._attributes_dataset is not None and self._attributes_samples is not None

    def _refresh(self):
        """"""
        # Todo: Write documentation
        self._load_meta_only = False
        self._readFromDatabase()
        self._loadedFromDatabase = True
        
    @abstractmethod
    def hasData(self):
        """Checks if dataset has data"""

    @abstractmethod
    def _readFromDatabase(self):
        """"""
        # Todo: Write documentation
        pass
    
    @abstractmethod
    def _read_from_dataframe(self, datatable : pd.DataFrame):
        """Reads databale from a dataframe. Required
        to insert a datatable. 

        Returns
        -------
        _type_
            _description_
        """
        pass 

    @abstractmethod
    def _read_meta(self, meta : Optional[DatasetSubmissionModel] = None):
        """"""
        pass 

    @staticmethod
    def buildInstrumentJson(db_id: int,
                            label: str,
                            name: str,
                            description: str) -> typing.Dict[str, typing.Any]:
        """"""
        # Todo: Write documentation
        return {"id": db_id,
                "label": label,
                "name": name,
                "description": description}

    @staticmethod
    def buildMetatextJsonItem(db_id: int, tag: str, title: str, text: str) -> typing.Dict[str, typing.Any]:
        """"""
        # Todo: Write documentation
        return {"id": db_id,
                "tag": tag,
                "title": title,
                "text": text}

    @staticmethod
    def buildAttributesJsonItem(db_id: int, attribute_parent_id: int,
                                attribute_tag: str, attribute: str, priority: int,
                                allow_as_filter: bool,
                                value_id: int, tag: str, value: str, details: str) -> typing.Dict[str, typing.Any]:
        """"""
        # Todo: Write documentation
        return {"attribute_id": db_id,
                "attribute_parent_id": attribute_parent_id,
                "attribute_tag": attribute_tag,
                "attribute": attribute,
                "priority": priority,
                "allow_as_filter": allow_as_filter,
                "id": value_id,
                "tag": tag,
                "value": value,
                "details": details}

    @staticmethod
    def buildSampleAttributesJsonItem(db_id: int,
                                      attribute_parent_id: int,
                                      attribute: str,
                                      priority: int,
                                      allow_as_filter: bool,
                                      grouping_json: typing.Dict) -> typing.Dict[str, typing.Any]:
        """"""
        # Todo: Write documentation
        # { 'att_substance': { } }
        return {'attribute_id': db_id,
                'attribute_parent_id': attribute_parent_id,
                'attribute': attribute,
                'priority': priority,
                'allow_as_filter': allow_as_filter,
                'values': grouping_json}

    @staticmethod
    def buildSampleAttributesJsonGroup(db_id: int, tag: str, value: str, details: str,
                                       samples: typing.List) -> typing.Dict[str, typing.Any]:
        """"""
        # Todo: Write documentation
        # { 'att_substance:none': xxx }
        return {'id': db_id,
                'tag': tag,
                'value': value,
                'details': details,
                'samples': samples}

    def getID(self) -> int:
        """Constructor"""
        # Todo: Write documentation
        return self._id

    def getDataTable(self) -> pd.DataFrame | None:
        """
        Returns the quantitative datatable (feature x samples) of the dataset.
        
        Returns
        -------
        pd.DataFrame | None 
            If dataset does not have a data table yet, None is returned. 
            Check with dataset.hasData() if data are available.
        """
        if not self._isDataTableLoaded():
            self._refresh()

        return self._cached_data_table

    def getLabel(self) -> str:
        """Constructor"""
        # Todo: Write documentation
        return self._label

    def getMetaJson(self, force_reload : bool = False, check_file : bool = True) -> DatasetSubmissionModel:
        """Returns the meta data. 
        
        Parameters
        ----------
        force_reload : bool, default False
            If True reloads the data using the function _read_meta() even if the data were loaded before.
        
        check_file : bool, default True 
            If true, checks if the file has been modified after the recent load. Only useful for 
            pandasfile database configuration. 
        
        Returns
        -------
        DatasetSubmissionModel
            The meta data. 
        """
        if DB_SETTINGS.db_handler == "pandafiles" and check_file and self._check_reload():
            self._read_meta() 
        elif not self._isMetaLoaded() or force_reload:
            self._read_meta() 
        return DatasetSubmissionModel(
            title=self._title,
            replicates=self._replicates,
            n_samples=len(self._sample_names),
            label=self._label,
            state=self._state,
            user_label=self._user_label,
            created_on=self._created_on,
            samples_attributes=self._attributes_samples,
            dataset_attributes=self._attributes_dataset,
            samples_genotypes=self._samples_genotypes,
            metatext=self._metatexts,
            collaborators=self._collaborators,
            sample_names=self._sample_names,
            timeline=self._timeline,
            runlist=self._runlist,
            links = self._urls)


    @deprecated(version='1.1', reason="Change of the data format: Please use the toJson(...) method.")
    def getLegacyMetaJson(self) -> typing.Dict[str, typing.Any]:
        """"""
        # Todo: Write documentation
        # Todo: Change to desired form
        if not self._isLoaded():
            self._refresh()

        metatexts = self._metatexts
        metatexts.pop("research_question", None)
        metatexts.pop("protein_of_interest", None)
        metatexts.pop("linked_data", None)

        json_experimental_info = []
        for key, item in metatexts.items():
            json_experimental_info.append({"title": item["title"],
                                           "details": item["text"]})

        json_groupings = {}
        for group_tag, group in self._attributes_samples.items():
            json_groupings[group["attribute"]] = {}
            for subgroup_tag, subgroup in group["values"].items():
                json_groupings[group["attribute"]][subgroup["value"]] = subgroup["samples"]

        json_grouping_names = list(json_groupings.keys())

        # ToDo: Remove creation of mock groups
        if len(json_grouping_names) != 2:
            samples_for_grouping = self._cached_data_table.columns.values.copy()
            random.shuffle(samples_for_grouping)
            json_grouping_names = ["MockRandomGroupingA", "MockRandomGroupingB"]
            json_groupings = {"MockRandomGroupingA": {"Accidential": [],
                                                        "Arbitrary": []},
                              "MockRandomGroupingB": {"Incidental": [],
                                                        "Indiscriminate": []}}

            for ix, item in enumerate(samples_for_grouping):
                if (ix % 2) == 0:
                    if(ix % 4) < 2:
                        json_groupings["MockRandomGroupingA"]["Accidential"].append(item)
                        json_groupings["MockRandomGroupingB"]["Incidental"].append(item)
                    else:
                        json_groupings["MockRandomGroupingA"]["Arbitrary"].append(item)
                        json_groupings["MockRandomGroupingB"]["Incidental"].append(item)
                else:
                    if(ix % 4) < 2:
                        json_groupings["MockRandomGroupingA"]["Accidential"].append(item)
                        json_groupings["MockRandomGroupingB"]["Indiscriminate"].append(item)
                    else:
                        json_groupings["MockRandomGroupingA"]["Arbitrary"].append(item)
                        json_groupings["MockRandomGroupingB"]["Indiscriminate"].append(item)

        cmap = ['Pastel1', 'Pastel2', 'Paired', 'Accent', 'Dark2', 'Set6', 'Set7', 'tab10', 'tab20', 'tab20b', 'tab20c']
        json_grouping_cmap = {}
        for item in json_grouping_names:
            json_grouping_cmap[item] = cmap.pop(random.randint(0, len(cmap)-1))

        return {"dataID": self._state,
                "Creation Date": self._created_on,
                "State": self._state,
                "Experimentator": self._experimentator,
                "Email": self._contact_email,
                "GroupName":  self._name_group,
                "Title": self._title,
                "Research Question": self._metatexts["research_question"] if "research_question" in self._metatexts else "Missing",
                "Protein of Interest": self._metatexts["protein_of_interest"] if "protein_of_interest" in self._metatexts else "Missing",
                "Linked data": self._metatexts["linked_data"] if "linked_data" in self._metatexts else "Missing",
                "Organism": self._attributes_dataset["att_organism"]["value"] if "att_organism" in self._attributes_dataset else "NA",
                "Type": self._attributes_dataset["att_experiment"]["value"] if "att_experiment" in self._attributes_dataset else "NA",
                "Instrument": self._instrument["id"],
                "Material": self._attributes_dataset["att_dataset"]["value"] if "att_dataset" in self._attributes_dataset else "NA",
                "Number Samples": self._cached_data_table.shape[1],
                "Number Replicates": len(self._replicates),
                "Number Groupings": len(json_grouping_names),
                "Experimental Info": json_experimental_info,
                "replicates": self._replicates,
                "groupingNames": json_grouping_names,
                "groupingCmap": json_grouping_cmap,
                "groupings": json_groupings
                }


    def getSamplesGenotypes(self) -> Tuple[pd.DataFrame,List[str]]:
        """_summary_

        Returns
        -------
        _type_
            _description_
        """
        meta_data = self.getMetaJson()
        sample_names = meta_data.sample_names 
        samples_genotypes = meta_data.samples_genotypes
        if len(samples_genotypes) == 0: return pd.DataFrame(), []
        sample_idces = pd.DataFrame(index = list(range(meta_data.n_samples)))
        attribute_mapper = value_mapper_from_dict(samples_genotypes) 
        sample_idces.loc[:,"genotype"] = sample_idces.index.map(attribute_mapper)
        genotypes = list(meta_data.samples_genotypes.keys())
        #replace indices with sample names
        sample_idces.index = sample_names
        return sample_idces, genotypes
        

    def getSamplesAttributes(self, add_genotype : bool = True) -> Tuple[pd.DataFrame, OrderedDict[str,List[str]]]:
        """
        Dataset function that maps the samples attributes to the sample names and is intended to be used in a HTTPResponse. 
        If multiple samples attribute values are assigned to a single sample, the tags are separated by a simple
        sample " ". 
        
        TODO : Should likely be moved to the PandaDataset and PostgreSQLDataset
        Returns
        -------
        samples_idces : pd.DataFrame 
            DataFrame where indices are the sample_names and the each column represents a samples attribute.
            The column name represent the attribute tag. 
        
        sample_attribute_by_name : OrderedDict 
            A dict with samples attribute names as keys and values as List[str] containing the sample attribute value
            tags. 
        """
        meta_data = self.getMetaJson()
        sample_names = meta_data.sample_names 
        samples_attributes = meta_data.samples_attributes #attributeTag -> sampleName Index
        genotypes = meta_data.samples_genotypes
        
            
        sample_idces = pd.DataFrame(index = list(range(meta_data.n_samples)))
        sample_attribute_by_name = OrderedDict()
        if not isinstance(samples_attributes,dict): TypeError("attributes_samples must be a dictionary.")
        for attribute_tag, sample_attribute_values  in  samples_attributes.items():
            #map sample attributes (attribute_value_tag,List Sample Indices)
            attribute_mapper = value_mapper_from_dict(sample_attribute_values) 
            sample_idces.loc[:,attribute_tag] = sample_idces.index.map(attribute_mapper)
            sample_attribute_by_name[attribute_tag] = list(sample_attribute_values.keys())
            
        if add_genotype and len(genotypes) > 0:
            genotype_mapper = value_mapper_from_dict(genotypes)
            sample_idces.loc[:,"att_genotype"] = sample_idces.index.map(genotype_mapper)
            sample_attribute_by_name["att_genotype"] = list(genotypes.keys())
        #replace indices with sample names
        sample_idces.index = sample_names
        return sample_idces, sample_attribute_by_name

    def isLoadedFromDatabase(self) -> bool:
        """"""
        # Todo: Write documentation
        return self._loadedFromDatabase

    def toJson(self) -> Dict[str, typing.Any]:
        """"""
        # Todo: Write documentation
        json = self.getMetaJson()
        json["data"] = self._cached_data_table

        return json

    @abstractmethod
    def write(self):
        """"""
        # Todo: Write documentation
        pass

    @abstractmethod
    def write_json(self , meta : DatasetSubmissionModel, update : bool):
        """Write only json data (e.g. store meta data for example when updated)"""
        pass
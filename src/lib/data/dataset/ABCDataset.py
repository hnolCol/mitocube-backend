# from __future__ import annotations

import pandas as pd 
import typing
from typing import List, Dict, Any
from pydantic import BaseModel, Field, field_serializer

from abc import abstractmethod
from deprecated import deprecated
from lib.DesignPatterns import JsonSerializable
from config.models.submissions.submissions import DatasetSubmissionModel
import random
from lib.DesignPatterns import JsonSerializable
import random
from collections import OrderedDict
from services.transforms import value_mapper_from_dict

class MCDataset(JsonSerializable):
    """Replacement for the Data.Dataset"""
    # Todo: Write documentation
    def __init__(self,
                 dataset_id: int = -1,
                 label: str = None,
                 state: str = None,
                 title: str = None,
                 #experimentator: str = None,
                 user_label : str = None,
                 collaborators : typing.List[str] = [],
               #  name_group: str = None,
               #  contact_email: str = None,  # ToDo: Countercheck default values
                 created_on: str = None,  # ToDo: Check DataType Date
                 uploaded_on: str = None,
                 data_table: pd.DataFrame = None,
                 metatexts: typing.Dict = None,
                 urls: typing.List = None,
                 replicates: typing.List[int] = [],
                 attributes_dataset: typing.Dict = None,
                 attributes_samples: typing.Dict = None,
                 sample_names : typing.List[str] = [],
                 timeline : typing.Dict = None,
                # instrument: typing.Dict = None,
                 loadFromDatabase: bool = False, 
                 load_meta_only : bool = False):  # ToDo: Check DataType Date
        """Constructor"""
        # Todo: Write documentation
        self._id = dataset_id
        self._label = label
        self._load_meta_only = load_meta_only
        self._cached_data_table = None

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
            #self._instrument = instrument

            self._title = title
            self._user_label = user_label
            self._collaborators = collaborators
            self._timeline = timeline
            #self._experimentator = experimentator
            #self._name_group = name_group

            self._created_on = created_on
            self._uploaded_on = uploaded_on

        # ToDo: Add Self stated updated / read date?

    def _isLoaded(self) -> bool:
        """"""
        # Todo: Write documentation
        return self._cached_data_table is not None and \
            self._attributes_dataset is not None and \
            self._attributes_samples is not None

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
    def _read_meta(self, label = None):
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

    def getDataTable(self) -> pd.DataFrame:
        """"""
        # Todo: Write documentation
        if not self._isLoaded():
            self._refresh()

        return self._cached_data_table

    def getLabel(self) -> str:
        """Constructor"""
        # Todo: Write documentation
        return self._label

    def getMetaJson(self) -> DatasetSubmissionModel:
        """"""
        # Todo: Write documentation
       
        if not self._isLoaded():
            self._read_meta() ##changed!
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
            metatext=self._metatexts,
            collaborators=self._collaborators,
            sample_names=self._sample_names,
            timeline=self._timeline)

        return {"id": self._id,
                "label": self._label,
                "state": self._state,
                "title": self._title,
                "user_label" : self._user_label,
                "email": self._contact_email,
                "created_on": self._created_on,
                #"date_uploaded_on": self._uploaded_on,
                #"instrument": self._instrument,
                "n_rows": self._cached_data_table.shape[0],
                "n_samples": self._cached_data_table.shape[1], #this excludes that there can be extra data in the table. 
                "metatexts": self._metatexts,

               # "urls": self._urls,
              #  "replicates": self._replicates,
             #   "attributes": self._attributes_dataset,
              #  "n_attributes": len(self._attributes_dataset),
                "attributes_samples": self._attributes_samples,
                "n_attribute_samples": len(self._attributes_samples)}


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

    def getSamplesAttributes(self):
        """
        """
        
        meta_data = self.getMetaJson()
        sample_names = meta_data.sample_names #mabe change to runnames
        samples_attributes = meta_data.samples_attributes #attributeTag -> sampleName Index
    
        sample_idces = pd.DataFrame(index = list(range(meta_data.n_samples)))
        sample_attribute_by_name = OrderedDict()
        if not isinstance(samples_attributes,dict): TypeError("attributes_samples must be a dictionary.")
        for attributes  in  samples_attributes.values():
            sample_attribute_name = attributes.name 
            sample_attribute_values = attributes.values 
            #switch keys and values to map samples indices
            attribute_mapper = value_mapper_from_dict(sample_attribute_values) 
            sample_idces.loc[:,sample_attribute_name] = sample_idces.index.map(attribute_mapper)
            sample_attribute_by_name[sample_attribute_name] = list(sample_attribute_values.keys())
        #replace indices with sample names
        sample_idces.index = sample_names
        return sample_idces, sample_attribute_by_name  # ToDo: Wrong return type

    def isLoadedFromDatabase(self) -> bool:
        """"""
        # Todo: Write documentation
        return self._loadedFromDatabase

    def toJson(self) -> typing.Dict[str, typing.Any]:
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
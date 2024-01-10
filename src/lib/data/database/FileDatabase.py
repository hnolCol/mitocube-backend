import os
from abc import ABC
from threading import Lock
from deprecated import deprecated

import json
from typing import Any, Dict, List

import pandas
import pandas as pd
import numpy as np

# from lib.DesignPatterns import SingletonABCMeta
from lib.data.database.ABCDatabase import MCDatabase, MCAttributes
from lib.data.dataset.ABCDataset import MCDataset
from lib.data.dataset.PandaDataset import PandaFileDataset

from config.settings.db import get_db_settings
# from config.settings.annotationsettings import get_annotation_settings

from config.models.attributes import AttributeModel, AttributeValueModel
from config.models.submissions.submissions import DatasetSubmissionModel

DB_SETTINGS = get_db_settings()


class PandaFileAttributes(MCAttributes):  # PostgreSQLAttributes
    """"""

    def __init__(self):
        super().__init__()

        self._lock = Lock()  # Synchronization primitive to make it multi-threading safe

        self.attributes = None
        self.attribute_values = None
        self.attributes_merged = None  # cached merged version of self.attributes and self.attribute_values

    def _import(self):
        """"""
        # Todo: Write documentation

        attribute_file_path = DB_SETTINGS.attribute_file

        try:
            with open(attribute_file_path, "r+") as attribute_json_file:
                json_attributes = json.load(attribute_json_file)

            self._attributes = pd.DataFrame.from_dict(json_attributes["attributes"])
            
            self._attribute_values = pd.DataFrame.from_dict(json_attributes["attribute_values"])

            self._attributes_merged = pd.merge(self._attributes, self._attribute_values, left_on="id", right_on="attribute_id")
            self._attributes_merged = self._attributes_merged.drop(columns=["attribute_id"])

            self._attributes_merged = self._attributes_merged.rename(columns={"id_x": "attribute_id",
                                                                              "parent_id": "attribute_parent_id",
                                                                              "tag_x": "attribute_tag",
                                                                              "name_x": "attribute",
                                                                              "id_y": "value_id",
                                                                              "tag_y": "value_tag",
                                                                              "name_y": "value"})

        except Exception as err:
            raise Exception("Unable to import attribute JSON file %s. Original Exception: %s" % (attribute_file_path, str(err)))

    def getAttributes(self, sort : bool = True) -> pd.DataFrame:
        """"""
        if sort:
            #sort attributes according to priority in descending order.
            return self._attributes.sort_values(by="priority", ascending=False)
        return self._attributes

    def getAttributeValues(self) -> pd.DataFrame:
        """
        Returns the full attribute value table as Panda DataFrame.
        """
        return self._attribute_values

    def getAttributeTable(self) -> pd.DataFrame:
        """
        Returns a table combining attributes and attributes values as Panda DataFrame.
        """
        return self._attributes_merged

    def getMandatoryAttributesForStage(self, stage : int) -> List[str]:
        """
        Returns a list of tags of mandatory attributes required from defined stage
        """
        return self._attributes.loc[self._attributes["min_state"] == stage, "tag"].tolist()

    def getMandatoryActivationAttributes(self) -> List[str]:
        """
        Returns a list of tags of mandatory attributes.
        """
        return self._attributes.loc[self._attributes["mandatory_for_active"], "tag"].tolist()

    def getMandatorySubmissionAttributes(self) -> List[str]:
        """
        Returns a list of tags of mandatory attributes.
        """
        return self._attributes.loc[self._attributes["mandatory_for_submission"], "tag"].tolist()

    def update(self):
        """
        Triggers a reload of the database.
        """
        self._import()

    # ToDo: Write / Insert / remove methods
    # def addAttribute(self, attribute : AttributeModel):
    #     """"""
    #     pass

    # def addAttributeValue(self, item : AttributeValueModel):
    #     """"""
    #     pass

    # def removeAttribute(self, tag : str):
    #     """"""
    #     pass

    # def removeAttributeValue(self, tag : str):
    #     """"""
    #     pass


class PandaFileDatabase(MCDatabase):
    """"""

    def __init__(self):
        """Constructor"""
        # Todo: Write documentation
        super().__init__()

        self._lock = Lock()  # Synchronization primitive to make it multi-threading safe

        self.attributes = None
        self.attribute_values = None
        self.attributes_merged = None  # cached merged version of self.attributes and self.attribute_values

        self.stat_nProteins = 42
        self.stat_nInstruments = 42
        self.stat_nUsers = 42
        self.stat_nTurnarounds = 42

        self._import_attributes()

    def doesLabelExists(self, dataset_label: str) -> bool:
        """"""
        return dataset_label in self.getDataIDs()

    def getAttributeTable(self) -> pd.DataFrame:
        """"""
        # Todo: Write documentation
        return self.attributes_merged

    def getSampleAttributeJSON(self, grouping_json: Dict = {}) -> Dict:
        """"""
        # Todo: Write documentation
        db_rows = self.attributes_merged[self.attributes_merged["value_tag"].isin(list(grouping_json.keys())) &
                                         self.attributes_merged["allow_for_measurement"]]

        json_groups = {}
        for ix, attribute in db_rows.iterrows():
            json_groups[attribute["value_tag"]] = MCDataset.buildSampleAttributesJsonGroup(db_id=attribute["value_id"],
                                                                                           tag=attribute["value_tag"],
                                                                                           value=attribute["value"],
                                                                                           details=attribute["details"],
                                                                                           samples=grouping_json[attribute["value_tag"]])

        return MCDataset.buildSampleAttributesJsonItem(db_id=db_rows["attribute_id"].iloc[0],
                                                       attribute_parent_id=db_rows["attribute_parent_id"].iloc[0],
                                                       attribute=db_rows["attribute"].iloc[0],
                                                       priority=db_rows["priority"].iloc[0],
                                                       allow_as_filter=db_rows["allow_as_filter"].iloc[0],
                                                       grouping_json=json_groups)

    def getDatasetAttributeJSON(self, tag: str = "") -> Dict:
        """"""
        # db.getDatasetAttributeJSON(tag="att_organism:up000005640")

        db_rows = self.attributes_merged[(self.attributes_merged["value_tag"] == tag) &
                                         self.attributes_merged["allow_for_dataset"]]

        if db_rows.shape[0] == 0:
            raise LookupError(f"No match for the attribute_value with the tag '{tag}'.")
        elif db_rows.shape[0] > 1:
            raise LookupError(f"No unique for the attribute_value with the tag '{tag}'.")

        return MCDataset.buildAttributesJsonItem(db_id=db_rows["attribute_id"].iloc[0],
                                                 attribute_parent_id=db_rows["attribute_parent_id"].iloc[0],
                                                 attribute_tag=tag,
                                                 attribute=db_rows["attribute"].iloc[0],
                                                 priority=db_rows["priority"].iloc[0],
                                                 allow_as_filter=db_rows["allow_as_filter"].iloc[0],
                                                 value_id=db_rows["value_id"].iloc[0],
                                                 tag=db_rows["value_tag"].iloc[0],
                                                 value=db_rows["value"].iloc[0],
                                                 details=db_rows["details"].iloc[0])

    def getDataLabels(self, sort_createdOn_desc: bool = False) -> List[str]:
        """Returns the list of dataset by their label (same as id for Pandas, different for SQL)"""
        self._lock.acquire()
        datasetFolders = []

        dir_root = DB_SETTINGS.db_datadir

        if not os.path.exists(dir_root):
            self._lock.release()
            raise FileNotFoundError(f"Invalid database path {dir_root}")

        for item in os.scandir(dir_root):
            if item.is_dir():
                datasetFolders.append(item.name)
        # ToDo: Implement sort_createdOn_desc #requires loading
        self._lock.release()

        return datasetFolders

    def getDataIDs(self,
                   n_limit: int = 42,  # ToDo: Implement Limit
                   n_offset: int = 0,  # ToDo: Implement Offset
                   sort_createdOn_desc: bool = False) -> List[str]:
        """"""
        
        labels = self.getDataLabels()

        ix_left = n_offset  # ToDo: Alternative ix_left = n_offset * (n_limit + 1)
        ix_right = ix_left + n_limit

        if ix_right > len(labels):
            ix_right = len(labels)  # ToDo: Different handling for out of index?

        if ix_left > len(labels):
            ix_left = len(labels)  # ToDo: Different handling for out of index?

        # ToDo: Implement sort_createdOn_desc

        return labels[ix_left:ix_right]

    def getJSONDatasets(self, labels: List[str] = []) -> Dict[str, DatasetSubmissionModel]:
        """"""
        # Todo: Write documentation
        datasets = {}
        labels_toQuery = []
        if len(labels) < 1:
            labels = self.getDataLabels()
            # labels = self.getAllDataIDs()

        for label in labels:
            if label in self._cached_datasets:
                #this is super error prone since if we change something in dataset then one has to 
                #remember to change here as well, otherwise chashed is not equal loaded. : 
                cached_dataset : MCDataset = self._cached_datasets[label] #to get easy coding, assign type.
                ##maybe just : 
                datasets[label] = cached_dataset.getMetaJson()
                
                # datasets[label] = DatasetSubmissionModel(
                #     title= cached_dataset._title,
                #     replicates= cached_dataset._replicates,
                #     n_samples=len(cached_dataset._sample_names),
                #     state= cached_dataset._state,
                #     label=cached_dataset._label, 
                #     user_label=cached_dataset._user_label,
                #     created_on=cached_dataset._created_on,
                #     samples_attributes=cached_dataset._attributes_samples,
                #     dataset_attributes=cached_dataset._attributes_dataset,
                #     metatext=cached_dataset._metatexts,
                #     collaborators=cached_dataset._collaborators,
                #     sample_names=cached_dataset._sample_names,
                #     timeline=cached_dataset._timeline,
                #     runlist=cached_dataset._runlist,
                #     links=cached_dataset._urls)
                
            else:
                labels_toQuery.append(label)

        if len(labels_toQuery) > 0:
            # ToDo: read json
            for label in labels_toQuery:
                #quick fix to just load_meta_only 
                datasets[label] = PandaFileDataset(label=label,load_meta_only=True).getMetaJson(force_reload=True)
            pass

        return datasets


    def getFeatures(self) -> List[str]:
        """
        Returns all features in the database 
        """
        data_labels = self.getDataLabels()

        features = []

        for label in data_labels:
            features.append(self.getDataset(label).getDataTable().index.values)
        
        return np.unique(features)

    def getFeatureTable(self, features : List[str]) -> Dict[str, Any]:  # ToDo: Or return panda?
        """"""
        # Todo: Write documentation
        featureTable = dict()

        if features is not None and features:
            pass  # featureTable = filled

        return featureTable

    def getDatasetsWithFeature(self, feature_key : str) -> List[str]:
        data_labels = self.getDataLabels()
        features = []
        for label in data_labels:
            features = self.getDataset(label).getDataTable().index
            if feature_key in features:
                features.append(label)
        
        return features

    def getDatasetsWithLabels(self, n_limit: int = 42, n_offset: int = 0, sort_createdOn_desc: bool = False) -> List[str]:
        pass

    # Todo: Write documentation

    def getNumberOfDatasets(self) -> int:
        """"""
        # Todo: Write documentation
        n_datasetFolders = 0

        dir_root = DB_SETTINGS.db_datadir

        if not os.path.exists(dir_root):
            raise FileNotFoundError(f"Invalid database path {dir_root}")

        for item in os.scandir(dir_root):
            if item.is_dir():
                n_datasetFolders += 1

        return n_datasetFolders
    
    def getMandatorySubmissionAttributes(self) -> List[AttributeModel]:
        """Should be maybe handled in frontend?"""
        attributes = self.attributes
        boolIdx = attributes["mandatory_for_submission"] == True
        return [AttributeModel(**attr) for attr in attributes.loc[boolIdx, :].to_dict(orient="records")]

    def getSize(self) -> int:
        """"""
        # Todo: Write documentation
        dir_root = DB_SETTINGS.db_datadir

        if not os.path.exists(dir_root): #actually no need since pydantic checks (however only at start)
            raise FileNotFoundError(f"Invalid database path {dir_root}")

        def get_dir_size(path: str):
            sum_size = 0
            with os.scandir(path) as it:
                for entry in it:
                    if entry.is_file():
                        sum_size += entry.stat().st_size
                    elif entry.is_dir():
                        sum_size += get_dir_size(entry.path)
            return sum_size

        return get_dir_size(dir_root)

    def _import_attributes(self):
        """"""
        # Todo: Write documentation
        try:
            # ToDo: read attribute values from file
            attribute_file_path = DB_SETTINGS.attribute_file
            with open(attribute_file_path, "r+") as attribute_json_file:
                json_attributes = json.load(attribute_json_file)
            
            self.attributes = pd.DataFrame.from_dict(json_attributes["attributes"])
            self.attribute_values = pd.DataFrame.from_dict(json_attributes["attribute_values"])

            self.attributes_merged = pd.merge(self.attributes, self.attribute_values, left_on="id", right_on="attribute_id")

            self.attributes_merged = pd.merge(self.attributes, self.attribute_values, left_on="id", right_on="attribute_id")
            self.attributes_merged = self.attributes_merged.drop(columns=["attribute_id"])
            self.attributes_merged = self.attributes_merged.rename(columns={"id_x": "attribute_id",
                                                                            "parent_id": "attribute_parent_id",
                                                                            "tag_x": "attribute_tag",
                                                                            "name_x": "attribute",
                                                                            "id_y": "value_id",
                                                                            "tag_y": "value_tag",
                                                                            "name_y": "value"})
        except Exception as err:
            raise Exception("Unable to import attribute JSON file: " + str(err))

   
# dataset = DB.getAllDataIDs()



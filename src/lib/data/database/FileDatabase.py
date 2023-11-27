import os 
import typing 
import json 
import pandas as pd 
import numpy as np 

from lib.data.database.ABCDatabase import MCDatabase
from lib.data.dataset.ABCDataset import MCDataset
from lib.data.dataset.PandaDataset import PandaFileDataset

from config.settings.db import get_db_settings
from config.models.attributes import Attribute
from config.models.submissions.submissions import SubmissionFromMetaDB

DB_SETTINGS = get_db_settings()


class PandaFileDatabase(MCDatabase):
    """"""
    # Todo: Write documentation

    def __init__(self):
        """Constructor"""
        # Todo: Write documentation
        super().__init__()


        self.attributes = None
        self.attribute_values = None
        self.attributes_merged = None  # cached merged version of self.attributes and self.attribute_values
        self._import_attributes()

    def contains(self, datasetIds: typing.List) -> int:
        """"""
        # Todo: Write documentation
        items = self.getDataIDs() 

        return [item in datasetIds for item in items] ##changed!!
    
    def labelExists(self, dataset_label: str) -> bool:
        """"""
        return dataset_label in self.getDataIDs()

    def getAttributeTable(self) -> pd.DataFrame:
        """"""
        # Todo: Write documentation
        return self.attributes_merged

    def getSampleAttributeJSON(self, grouping_json: typing.Dict = {}) -> typing.Dict:
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

    def getDatasetAttributeJSON(self, tag: str = "") -> typing.Dict:
        """"""
        # db.getDatasetAttributeJSON(tag="att_organism:human")

        db_rows = self.attributes_merged[(self.attributes_merged["value_tag"] == tag) &
                                         self.attributes_merged["allow_for_dataset"]]

        if db_rows.shape[0] == 0:
            raise Exception(f"No match for the attribute_value with the tag '{tag}'.")
        elif db_rows.shape[0] > 1:
            raise Exception(f"No unique for the attribute_value with the tag '{tag}'.")

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

    def getAllDataIDs(self, sort_createdOn_desc: bool = False) -> typing.List[str]:
        """"""
        # Todo: Write documentation
        datasetFolders = []

        dir_root = DB_SETTINGS.db_datadir

        if not os.path.exists(dir_root):
            raise Exception(f"Invalid database path {dir_root}")

        for item in os.scandir(dir_root):
            if item.is_dir():
                datasetFolders.append(item.name)
        # ToDo: Implement sort_createdOn_desc #requires loading
        return datasetFolders
    
    def getAllDataLabels(self, sort_createdOn_desc: bool = False) -> typing.List[str]:
        """Returns the list of dataset by their label (same as id for Pandas, different for SQL)"""
        return self.getAllDataIDs()

    def getDataIDs(self,
                   n_limit: int = 42,  # ToDo: Implement Limit
                   n_offset: int = 0,  # ToDo: Implement Offset
                   sort_createdOn_desc: bool = False) -> typing.List[str]:
        """"""
        datasetFolders = self.getAllDataIDs()

        ix_left = n_offset  # ToDo: Alternative ix_left = n_offset * (n_limit + 1)
        ix_right = ix_left + n_limit

        if ix_right > len(datasetFolders):
            ix_right = len(datasetFolders)  # ToDo: Different handling for out of index?

        if ix_left > len(datasetFolders):
            ix_left = len(datasetFolders)  # ToDo: Different handling for out of index?

        # ToDo: Implement sort_createdOn_desc

        return datasetFolders[ix_left:ix_right]

    def getJSONDatasets(self, labels: typing.List[str] = []) -> typing.Dict[str, SubmissionFromMetaDB]:
        """"""
        # Todo: Write documentation
        datasets = {}
        labels_toQuery = []
        if len(labels) < 1:
            labels = self.getAllDataIDs()

        for label in labels:
            if label in self._cached_datasets:
                ##TO DO. Change this and incorporate pydantic model.
                datasets[label] = SubmissionFromMetaDB(
                    title= self._cached_datasets[label]._title,
                    replicates= self._cached_datasets[label]._replicates,
                    n_samples=len(self._cached_datasets[label]._sample_names),
                    state= self._cached_datasets[label]._state,
                    label=self._cached_datasets[label]._label, 
                    user_label=self._cached_datasets[label]._user_label,
                    created_on=self._cached_datasets[label]._created_on,
                    samples_attributes=self._cached_datasets[label]._attributes_samples,
                    dataset_attributes=self._cached_datasets[label]._attributes_dataset,
                    metatext=self._cached_datasets[label]._metatexts,
                    collaborators=self._cached_datasets[label]._collaborators,
                    sample_names=self._cached_datasets[label]._sample_names,
                    timeline=self._cached_datasets[label]._timeline)
                
                # datasets[label] = {"id": self._cached_datasets[label]._id,
                #                    "user_id" : self._cached_datasets[label]._user_id,
                #                    "label": self._cached_datasets[label]._label,
                #                   # "email": self._cached_datasets[label]._contact_email, #defined by user id 
                #                    "state": self._cached_datasets[label]._state,
                #                    #"instrument": self._cached_datasets[label]._instrument,
                #                    "title": self._cached_datasets[label]._title,
                #                   # "experimentator": self._cached_datasets[label]._experimentator, #defined by user id
                #                    #"group_name": self._cached_datasets[label]._name_group, #defined by user id 
                #                    "created_on": self._cached_datasets[label]._created_on,
                #                    "sample_attributes" : self._cached_datasets[label]._attributes_samples
                                   
                                   #date_uploaded_on": self._cached_datasets[label]._uploaded_on}
            else:
                labels_toQuery.append(label)

        if len(labels_toQuery) > 0:
            # ToDo: read json
            for label in labels_toQuery:
                #quick fix to just load_meta_only 
                datasets[label] = PandaFileDataset(label=label,load_meta_only=True).get_meta_data()
            pass

        return datasets
    
       
    def getFeatures(self) -> typing.List[str]:
        """
        Returns all features in the database 
        """
        data_labels = self.getAllDataLabels()
        features = []
        for label in data_labels:
            features.append(self.getDataset(label).getDataTable().index.values)
        
        return np.unique(features)

    
    def getDatasetsWhereFeatureIsFound(self, feature_id : str) -> typing.List[str]:
        """Returns all datasets that contain a specific feature"""
        data_labels = self.getAllDataLabels()
        features = []
        for label in data_labels:
            features = self.getDataset(label).getDataTable().index
            if feature_id in features:
                features.append(label)
        
        return features

    def getNumberOfDatasets(self) -> int:
        """"""
        # Todo: Write documentation
        n_datasetFolders = 0

        dir_root = DB_SETTINGS.db_datadir

        if not os.path.exists(dir_root):
            raise Exception(f"Invalid database path {dir_root}")

        for item in os.scandir(dir_root):
            if item.is_dir():
                n_datasetFolders += 1

        return n_datasetFolders
    
    def getMandatorySubmissionAttributes(self) -> typing.List[Attribute]:
        """Should be maybe handled in frontend?"""
        attributes = self.attributes
        boolIdx = attributes["mandatory_for_submission"] == True
        return [Attribute(**attr) for attr in attributes.loc[boolIdx,:].to_dict(orient="records")]

    def getSize(self) -> int:
        """"""
        # Todo: Write documentation
        dir_root = DB_SETTINGS.db_datadir

        if not os.path.exists(dir_root): #actually no need since pydantic checks (however only at start)
            raise Exception(f"Invalid database path {dir_root}")

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



# DB = PandaFileDatabase()
# dataset = DB.getAllDataIDs()



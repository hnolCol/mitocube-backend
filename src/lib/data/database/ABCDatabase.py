from __future__ import annotations

from datetime import timedelta

import pandas as pd
from typing import List, Dict, Any
from abc import abstractmethod
from collections import OrderedDict
from lib.data.dataset.ABCDataset import MCDataset

from lib.DesignPatterns import SingletonABCMeta, ExpiringValue

from config.settings.db import get_db_settings
from config.models.attributes import Attribute
from config.models.submissions.submissions import DatasetSubmissionModel

DB_SETTINGS = get_db_settings()


class InvalidDatasetLabelError(Exception):
    pass


class MCDatabase(metaclass=SingletonABCMeta):
    """"""
    # Todo: Write documentation

    def __init__(self):  # ToDo: Check DataType Date
        """Singleton Constructor"""
        # Todo: Write documentation
        self._cached_datasets = OrderedDict()

        # otherTestiTestValue = 69

        # def doTestiTest():
        #     print(" >>> doTestiTest() !!!")
        #     return otherTestiTestValue

        # self.testitest = ExpiringValue[int](expireTime=timedelta(seconds = 5),
        #                                     value=42,
        #                                     updateProcess = doTestiTest)


    def clearCachedDatasets(self):
        """
        Clears the cached of (memory) stored datasets.
        """
        # Todo: Write documentation
        self._cached_datasets.clear()

    @abstractmethod
    def doesLabelExists(self, dataset_label : str) -> bool:
        """
        Returns true if the dataset label exists.
        """
        pass

    @abstractmethod
    def getAttributeTable(self) -> pd.DataFrame:
        """
        Returns the full attribute table as Panda DataFrame.
        """
        pass

    @abstractmethod
    def getSampleAttributeJSON(self, grouping_json: Dict = {}) -> Dict:
        """

        """
        # Todo: Write documentation
        pass

    def getDataset(self, label: str) -> MCDataset:
        """
        Returns a dataset object with the defined label. If it is cached, take it from memory, otherwise read it from the long-term database. Raises an InvalidDatasetLabelError exception if the dataset (label) is not found.
        """
        dataset = None

        if label in self._cached_datasets.keys():
            dataset = self._cached_datasets[label]
            self._cached_datasets.move_to_end(label, last=True)
        else:
            # if DB_SETTINGS.db_handler == "postgresql":
            #     from lib.data.dataset.PostgreSQLDataset import PostgreSQLDataset
            #     dataset = PostgreSQLDataset(label=label, loadFromDatabase=True)
            # elif DB_SETTINGS.db_handler == "pandafiles":
            if DB_SETTINGS.db_handler == "pandafiles":
                from lib.data.dataset.PandaDataset import PandaFileDataset
                dataset = PandaFileDataset(label=label, loadFromDatabase=True)
            else:
                raise Exception("Invalid MitoCubeDatabase configuration. Only 'postgresql' and 'pandafiles' are supported.")

            if len(self._cached_datasets) > int(DB_SETTINGS.db_ip):
                self._cached_datasets.popitem(last=False)

            self._cached_datasets[label] = dataset

        return dataset

    @abstractmethod
    def getJSONDatasets(self, labels: List[str] = []) -> Dict[str, DatasetSubmissionModel]:
        """

        """
        # Todo: Write documentation
        pass

    def getDatasets(self, labels: List[str] = []) -> Dict[str, MCDataset]:
        """
        Returns a dictionary of the datasets defined in labels. Uses the database labels as keys. Labels with no matching dataset in the database will be silently ignored and an e
        """
        # Todo: Write documentation
        datasets = {}

        if len(labels) < 1:
            labels = self.getAllDataLabels()

        for label in labels:
            if label in self._cached_datasets.keys():
                datasets[label] = self._cached_datasets[label]
            else:
                datasets[label] = self.getDataset(label)

        return datasets

    @abstractmethod
    def getDatasetAttributeJSON(self, tag: str = "") -> Dict:
        """"""
        # Todo: Write documentation
        pass

    @abstractmethod
    def getAllDataLabels(self, sort_createdOn_desc: bool = False) -> List[str]:
        """
        Equivalent to getAllDataIDs() but returns a list of database string labels instead of numerical ids.
        """
        # Todo: Write documentation
        pass

    @abstractmethod
    def getDatasetsWithLabels(self,
                              n_limit: int = 42,
                              n_offset: int = 0,
                              sort_createdOn_desc: bool = False) -> List[str]:
        """"""
        # Todo: Write documentation
        pass

    @staticmethod
    def getDatabase() -> MCDatabase:
        """
        Returns a (singleton) database object depending on the settings. Either A PandaFileDatabase or PostgreSQLDatabase.
        """
        if DB_SETTINGS.db_handler == "postgresql":
            from lib.data.database.ProstgreSQLDatabase import PostgreSQLDatabase
            return PostgreSQLDatabase()
        elif DB_SETTINGS.db_handler == "pandafiles":
            from lib.data.database.FileDatabase import PandaFileDatabase
            return PandaFileDatabase()
        else:
            raise Exception("Invalid MitoCubeDatabase configuration. Only 'postgresql' and 'pandafiles' are supported.")


    @abstractmethod
    def getMandatorySubmissionAttributes(self) -> List[Attribute]:
        """
        Returns a list of mandatory attributes.
        """
        pass

    @abstractmethod
    def getNumberOfDatasets(self) -> int:
        """
        Returns numbers of datasets saved in the database.
        """
        # Todo: Write documentation
        pass

    @abstractmethod
    def getFeatures(self) -> List:
        """
        Returns all features in the database 
        """
        pass

    @abstractmethod
    def getFeatureTable(self, features : List[str]) -> Dict[str, Any]:  # ToDo: Or return panda?
        """
        Returns a Diction (or panda.Dataframe) of the all features or features requested (argument features).
        """
        pass

    @abstractmethod
    def getDatasetsWithFeature(self, feature_id : str) -> List:
        """
        Returns all datasets that contain a specific feature as List.
        """
        pass

    @abstractmethod
    def getSize(self) -> int:
        """
        Returns used size for data in bytes.
        """
        # Todo: Write documentation
        pass

    def insert(obj: MCDataset):
        """
        Adds/Writes new MCDataset to the database.
        """
        # Todo: Write documentation
        obj.write()

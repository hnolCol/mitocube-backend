import pandas as pd 
import typing 
from abc import abstractmethod
from collections import OrderedDict
from lib.data.dataset.ABCDataset import MCDataset

from lib.data.DesignPatterns import SingletonABCMeta

from config.settings.db import get_db_settings
from config.models.attributes import Attribute
from config.models.submissions.submissions import SubmissionFromMetaDB

DB_SETTINGS = get_db_settings()


class MCDatabase(metaclass=SingletonABCMeta):
    """"""
    # Todo: Write documentation

    def __init__(self):  # ToDo: Check DataType Date
        """Constructor"""
        # Todo: Write documentation
        self._cached_datasets = OrderedDict()

    def clearCachedDatasets(self):
        """"""
        # Todo: Write documentation
        self._cached_datasets.clear()

    @abstractmethod
    def contains(self, datasetIds: typing.List) -> int:
        """"""
        # Todo: Write documentation
        pass

    @abstractmethod
    def labelExists(self,dataset_label : str) -> bool:
        """
        Returns true if the dataset label exists. 
        """
        pass

    def insert(obj: MCDataset):
        """"""
        # Todo: Write documentation
        obj.write()

    @abstractmethod
    def getAttributeTable(self) -> pd.DataFrame:
        """"""
        # Todo: Write documentation
        pass

    @abstractmethod
    def getSampleAttributeJSON(self, grouping_json: typing.Dict = {}) -> typing.Dict:
        """"""
        # Todo: Write documentation
        pass

    def getDataset(self, label: str) -> MCDataset:
        """"""
        # Todo: Write documentation
        dataset = None

        if label in self._cached_datasets.keys():
            dataset = self._cached_datasets[label]
            self._cached_datasets.move_to_end(label, last=True)
        else:
            if DB_SETTINGS.db_handler == "postgresql":
                from lib.data.dataset.PostgreSQLDataset import PostgreSQLDataset
                dataset = PostgreSQLDataset(label=label, loadFromDatabase=True)
            elif DB_SETTINGS.db_handler == "pandafiles":
                from lib.data.dataset.PandaDataset import PandaFileDataset
                dataset = PandaFileDataset(label=label, loadFromDatabase=True)
            else:
                raise Exception("Invalid MitoCubeDatabase configuration. Only 'postgresql' and 'pandafiles' are supported.")

            if len(self._cached_datasets) > int(DB_SETTINGS.db_ip):
                self._cached_datasets.popitem(last=False)

            self._cached_datasets[label] = dataset

        return dataset

    @abstractmethod
    def getJSONDatasets(self, labels: typing.List[str] = []) -> typing.Dict[str, SubmissionFromMetaDB]:
        """"""
        # Todo: Write documentation
        pass

    def getDatasets(self, labels: typing.List[str] = []) -> typing.Dict[str, MCDataset]:
        """"""
        # Todo: Write documentation
        datasets = {}

        if len(labels) < 1:
            labels = self.getAllDataIDs()

        for label in labels:
            if label in self._cached_datasets.keys():
                datasets[label] = self._cached_datasets[label]
            else:
                datasets[label] = self.getDataset(label)

        return datasets

    @abstractmethod
    def getDatasetAttributeJSON(self, tag: str = "") -> typing.Dict:
        """"""
        # Todo: Write documentation
        pass

    @abstractmethod
    def getAllDataIDs(self, sort_createdOn_desc: bool = False) -> typing.List[str]:
        """"""
        # Todo: Write documentation
        pass

    @abstractmethod
    def getAllDataLabels(self, sort_createdOn_desc: bool = False) -> typing.List[str]:
        """"""
        # Todo: Write documentation
        pass

    @abstractmethod
    def getDataIDs(self,
                   n_limit: int = 42,
                   n_offset: int = 0,
                   sort_createdOn_desc: bool = False) -> typing.List[str]:
        """"""
        # Todo: Write documentation
        pass

    @staticmethod
    def getDatabase():
        """"""
        # Todo: Write documentation
        # https: // stackoverflow.com / questions / 33533148 / how - do - i - type - hint - a - method -
        # with-the - type - of - the - enclosing -class
        if DB_SETTINGS.db_handler == "postgresql":
            from lib.data.database.ProstgreSQLDatabase import PostgreSQLDatabase
            return PostgreSQLDatabase()
        elif DB_SETTINGS.db_handler =="pandafiles":
            from lib.data.database.FileDatabase import PandaFileDatabase
            return PandaFileDatabase()
        else:
            raise Exception("Invalid MitoCubeDatabase configuration. Only 'postgresql' and 'pandafiles' are supported.")


    @abstractmethod
    def getMandatorySubmissionAttributes(self) -> typing.List[Attribute]:
        """Returns the list of dataset attributes that are mandatory."""

    @abstractmethod
    def getNumberOfDatasets(self) -> int:
        """"""
        # Todo: Write documentation
        pass

    @abstractmethod
    def getFeatures(self) -> list:
        """
        Returns all features in the database 
        """
        return []

    @abstractmethod
    def getDatasetsWhereFeatureIsFound(self, feature_id : str) -> list:
        """Returns all datasets that contain a specific feature"""


    @abstractmethod
    def getSize(self) -> int:
        """"""
        # Todo: Write documentation
        pass

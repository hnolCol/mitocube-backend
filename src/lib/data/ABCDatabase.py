from __future__ import annotations

# from abc import abstractmethod
from collections import OrderedDict
from typing import Dict, Type, Self

# from datetime import datetime, timedelta
# from deprecated import deprecated

import lib.data as dlib

from config import get_system_settings
from lib.designpatterns import SingletonABCMeta

# import pandas as pd
#
# from lib.data.dataset.ABCDataset import MCDataset
# from lib.DesignPatterns import SingletonABCMeta  # , ExpiringValue
#
# from config.settings.db import get_db_settings
# from config.models.attributes import AttributeModel
# from config.models.submissions.submissions import DatasetSubmissionModel

class ABCDataError(Exception):
    pass

class ABCDatabaseError(ABCDataError):
    pass

class ABCDatabase(dlib.FlexDataClass, metaclass=SingletonABCMeta):

    def __init__(self):
        self._cached_datasets: OrderedDict[str, dlib.ABCDataset] = OrderedDict()

    def clear_cached_datasets(self):
        self._cached_datasets.clear()

    @classmethod
    def _get_class_rulings(cls) -> Dict[str, Self]:
        import lib.data.sql.postgresql as sqllib
        return {"postgresql": sqllib.PostgreSQLDatabase}

    # def get_dataset(self, label: str) -> dlib.ABCDataset:
    #     dataset: dlib.ABCDataset | None = None
    #
    #     if label in self._cached_datasets.keys():
    #         dataset = self._cached_datasets[label]
    #         self._cached_datasets.move_to_end(label, last=True)
    #         return dataset
    #
    #     CONF = get_system_settings()
    #
    #     if CONF.db_handler == "postgresql":
    #         from lib.data.sql.postgresql.PostgreSQLDatabase import
    #         database
    #     elif CONF.db_handler == "pandafiles":  # todo: Implement "pandafiles" db_handler
    #         raise ABCDatabaseError("pandafiles is not implemented yet!")
    #         #from lib.data.dataset.PandaDataset import PandaFileDataset
    #         # dataset = None  # PandaFileDataset(label=label, loadFromDatabase=True)
    #     else:
    #         raise ABCDatabaseError("getDataset(...) is not implemented yet!")
    #
    #     if len(self._cached_datasets) > 42:  # todo: change me to int(DB_SETTINGS.db_ip):
    #         self._cached_datasets.popitem(last=False)
    #
    #     self._cached_datasets[label] = dataset
    #
    #     return dataset

    # @staticmethod
    # def get_database() -> ABCDatabase:
    #     CONF = get_system_settings()
    #
    #     if CONF.db_handler == "postgresql":
    #         from lib.data.sql.postgresql import PostgreSQLDatabase
    #         return lib.data.sql.postgresql.PostgreSQLDatabase()
    #     elif CONF.db_handler == "panda_files":
    #         raise ABCDatabaseError("The db handler panda_files is not implemented yet!")
    #     else:
    #         raise ABCDatabaseError("Invalid MitoCubeDatabase configuration. Only 'postgresql' and 'pandafiles' are supported.")
    #

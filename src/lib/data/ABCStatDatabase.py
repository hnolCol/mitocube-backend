from __future__ import annotations
from abc import ABC, abstractmethod

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


class ABCStatDatabaseError(dlib.ABCDataError):
    pass

class ABCStatDatabase(dlib.FlexDataClass, metaclass=SingletonABCMeta):

    @classmethod
    def _get_class_rulings(cls) -> Dict[str, Self]:
        import lib.data.sql.postgresql as sqllib
        return {"postgresql": sqllib.PostgreSQLStatDatabase}

    @staticmethod
    @abstractmethod
    def get_n_submissions() -> int:  # Move definition to ABCDatabase
        pass

    @staticmethod
    @abstractmethod
    def get_n_active_datasets() -> int:  # Move definition to ABCDatabase
        pass

    @staticmethod
    @abstractmethod
    def get_n_pg_features() -> int:  # Move definition to ABCDatabase
        pass

    @staticmethod
    @abstractmethod
    def get_n_genotypes() -> int:  # Move definition to ABCDatabase
        pass

    @staticmethod
    @abstractmethod
    def get_n_active_users() -> int:  # Move definition to ABCDatabase
        pass

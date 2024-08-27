from __future__ import annotations

from abc import abstractmethod
from typing import List
from threading import Lock
from typing import Dict, Type, Self
import os
import pandas as pd

import lib.data as dlib

from lib.designpatterns import SingletonABCMeta
from config import get_system_settings


class ABCFeatureDatabaseError(dlib.ABCDataError):
    pass


class ABCFeatureDatabase(dlib.FlexDataClass, metaclass=SingletonABCMeta):

    @classmethod
    def _get_class_rulings(cls) -> Dict[str, Self]:
        import lib.data.sql.postgresql as sqllib
        return {"postgresql": sqllib.PostgreSQLFeatureDatabase}

    @abstractmethod
    def read(self):
        pass

    @abstractmethod
    def reset(self):
        pass


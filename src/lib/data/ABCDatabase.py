from __future__ import annotations

from abc import abstractmethod
# from abc import abstractmethod
from collections import OrderedDict
from typing import Dict, List, Type, Self, Tuple

# from datetime import datetime, timedelta

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
    @classmethod
    def _get_class_rulings(cls) -> Dict[str, Self]:
        import lib.data.sql.postgresql as sqllib
        return {"postgresql": sqllib.PostgreSQLDatabase}

    def get_attribute_by_id(self, db_id: int) -> dlib.ABCAttribute:
        return dlib.ABCAttribute.get_class().objectify_with_id[db_id]

    def get_attribute_by_tag(self, tag: str) -> dlib.ABCAttribute:
        return dlib.ABCAttribute.get_class().objectify_with_tag(tag)

    def get_trait_by_id(self, db_id: int) -> dlib.ABCTrait:
        return dlib.ABCTrait.get_class().objectify_with_id(db_id)

    def get_trait_by_tag(self, tag: str) -> dlib.ABCTrait:
        return dlib.ABCTrait.get_class().objectify_with_id(tag)

    @staticmethod
    @abstractmethod
    def query_trait_ids(trait_query: str | None = None, trait_tags: List[str] | None = None) -> List[id]:
        pass

    @staticmethod
    @abstractmethod
    def query_datasets_ids(query: str | None = None,
                           states: List[int] | None = None,
                           feature_keys: List[str] | None = None,
                           trait_tags: List[str] | None = None,
                           trait_ids: List[int] | None = None,
                           genotype_labels: List[str] | None = None,
                           usernames: List[str] | None = None,
                           limit_to_n: int | None = None,
                           limit_offset: int = 0) -> Tuple[List[id], List[str]]:
        pass

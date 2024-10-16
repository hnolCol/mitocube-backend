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

class CachedDatabase(dlib.ABCDatabase):  # ToDo: Implement CachedDatabase
    # https://seanblanchfield.com/2009/02/python-memoize-with-expiry
    # https://github.com/python/cpython/blob/3.13/Lib/functools.py
    # clear function maybe calling self.get_attribute_by_id.clear_cache() ?
    # But how to best have a shared cache between function. implementing everything without decorator?

    def __init__(self):
        super().__init__()
        self._cached_attributes: Dict[id, dlib.ABCAttribute] = {}
        self._cached_attribute_tags: Dict[str, id] = {}
        self._cached_traits: Dict[id, dlib.ABCTrait] = {}
        self._cached_trait_tags: Dict[str, id] = {}

        # self._cached_datasets: OrderedDict[str, dlib.ABCDataset] = OrderedDict()
        # self._cached_instruments: OrderedDict[str, dlib.ABCInstrument] = OrderedDict()

    def clear_cache(self):
        self.clear_cached_attributes_and_traits()

        # self.clear_cached_datasets()
        # self.clear_cached_instruments()

    def clear_cached_attributes_and_traits(self):
        self._cached_attributes = {}
        self._cached_attribute_tags = {}
        self._cached_traits = {}
        self._cached_trait_tags = {}

#    def clear_cached_datasets(self):
#        self._cached_datasets.clear()

#    def clear_cached_instruments(self):
#        self._cached_instruments.clear()

    def get_attribute_by_id(self, db_id: int) -> dlib.ABCAttribute:
        if db_id not in self._cached_attributes.keys():
            obj = super().get_attribute_by_id(db_id=db_id)
            self._cached_attributes[db_id] = obj
            self._cached_attribute_tags[obj.get_tag()] = db_id

        return self._cached_attributes[db_id]

    def get_attribute_by_tag(self, tag: str) -> dlib.ABCAttribute:
        if tag not in self._cached_attribute_tags.keys():
            obj: dlib.ABCAttribute = super().get_attribute_by_tag(tag=tag).objectify_with_tag(tag)
            self._cached_attributes[obj.get_id()] = obj
            self._cached_attribute_tags[tag] = obj.get_id()

        return self._cached_attributes[self._cached_attribute_tags[tag]]

    def get_trait_by_id(self, db_id: int) -> dlib.ABCTrait:
        if db_id not in self._cached_traits.keys():
            obj: dlib.ABCTrait = super().get_trait_by_id(db_id=db_id)
            self._cached_traits[db_id] = obj
            self._cached_trait_tags[obj.get_tag()] = db_id

            parent = obj.get_attribute()

            while parent is not None:  # Cache parent and possible grand-attributes
                if parent.get_id() not in self._cached_attributes.keys():
                    self._cached_attributes[parent.get_id()] = parent
                    self._cached_attribute_tags[parent.get_tag()] = parent.get_id()
                parent = parent.get_parent_attribute()

        return self._cached_traits[db_id]

    def get_trait_by_tag(self, tag: str) -> dlib.ABCTrait:
        if tag not in self._cached_trait_tags.keys():
            obj: dlib.ABCTrait = super().get_trait_by_tag(tag=tag)
            self._cached_traits[obj.get_id()] = obj
            self._cached_trait_tags[tag] = obj.get_id()

            parent = obj.get_attribute()

            while parent is not None:  # Cache parent and possible grand-attributes
                if parent.get_id() not in self._cached_attributes.keys():
                    self._cached_attributes[parent.get_id()] = parent
                    self._cached_attribute_tags[parent.get_tag()] = parent.get_id()
                parent = parent.get_parent_attribute()

        return self._cached_traits[self._cached_trait_tags[tag]]

    def preload_attributes_and_traits(self):
        self._cached_traits.clear()

        at: dlib.ABCAttribute = dlib.ABCAttribute.get_class()
        tr: dlib.ABCTrait = dlib.ABCTrait.get_class()

        self._cached_attributes = at.get_all_attributes()
        self._cached_attribute_tags = {obj.get_tag(): obj for tag, obj in self._cached_attributes.items()}

        self._cached_traits = tr.get_all_traits(attributes = self._cached_attributes)
        self._cached_trait_tags = {obj.get_full_tag(): obj for tag, obj in self._cached_traits.items()}

    @staticmethod
    @abstractmethod
    def query_trait_ids(trait_query: str | None = None, trait_tags: List[str] | None = None) -> List[id]:
        pass

    @staticmethod
    @abstractmethod
    def query_datasets_ids(query: str | None = None, states: List[int] | None = None,
                           feature_keys: List[str] | None = None, trait_tags: List[str] | None = None,
                           trait_ids: List[int] | None = None, genotype_labels: List[str] | None = None,
                           usernames: List[str] | None = None, limit_to_n: int | None = None, limit_offset: int = 0) -> Tuple[List[id], List[str]]:
        pass

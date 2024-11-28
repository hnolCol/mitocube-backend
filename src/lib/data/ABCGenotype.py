from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Self

import lib.data as dlib

import pandas as pd
# import copy
# from enum import Enum
# from typing import Self

# class CSVDataTableType(Enum):
#     UNKNOWN = -1
#     WIDE_FULL_DATA = 1

class ABCGenotypeError(dlib.ABCDatasetError):
    pass

class ABCGenotypeNotFoundError(ABCGenotypeError):
    pass

class ABCGenotype(ABC, dlib.FlexDataClass):

    def __init__(self, label: str, name: str, trait_tree: dlib.ABCTraitTree, created_by: dlib.ABCUser,
                 db_id: int | None = None, description: str | None = None, is_selectable: bool = True,
                 created_on: datetime = datetime.now(tz = None)):
        self._id: int | None = db_id
        self._label: str = label
        self._name: str = name
        self._description: str | None = description
        self._is_selectable: bool = is_selectable
        self._trait_tree: dlib.ABCTraitTree = trait_tree
        self._created_by: dlib.ABCUser = created_by
        self._created_on: datetime = created_on


    @classmethod
    def _get_class_rulings(cls) -> Dict[str, Self]:  # ToDo: Update return values!
        import lib.data.sql.postgresql as sqllib
        return {"postgresql": sqllib.PostgreSQLGenotype}

    def is_selectable(self) -> bool:
        return self._is_selectable

    def get_id(self) -> int | None:
        return self._id

    def get_label(self) -> str:
        return self._label

    def get_name(self) -> str:
        return self._name

    def get_description(self) -> str | None:
        return self._description

    def get_trait_tree(self) -> dlib.ABCTraitTree:
        return self._trait_tree

    def get_created_by(self) -> dlib.ABCUser:
        return self._created_by

    def get_created_on(self) -> datetime:
        return self._created_on

    def set(self, label: str, name: str, description: str | None = None, is_selectable: bool = True):
        self._label: str = label
        self._name: str = name
        self._description: str | None = description
        self._is_selectable: bool = is_selectable

    def set_description(self, description: str | None = None):
        self._description: str | None = description

    def set_is_selectable(self, is_selectable: bool = True):
        self._is_selectable: bool = is_selectable

    def set_name(self, name: str, ):
        self._name: str = name

    def set_label(self, label: str, ):
        self._label: str = label

    @classmethod
    @abstractmethod
    def objectify_with_id(cls, db_id: int) -> ABCGenotype:
        pass

    @classmethod
    @abstractmethod
    def objectify_with_label(cls, label: str) -> ABCGenotype:
        pass

    @classmethod
    @abstractmethod
    def objectify_with_dataset_id(cls, dataset_id: int) -> Dict[str, ABCGenotype]:
        pass

    @classmethod
    @abstractmethod
    def objectify_with_dataset_label(cls, dataset_label: str) -> Dict[str, ABCGenotype]:
        pass

    @classmethod
    @abstractmethod
    def objectify_with_sample_id(cls, sample_id: int) -> Dict[str, ABCGenotype]:
        pass

    @classmethod
    @abstractmethod
    def objectify_with_sample_label(cls, sample_id: str, dataset_id: int) -> Dict[str, ABCGenotype]:
        pass

    @abstractmethod
    def write_to_db(self):
        pass
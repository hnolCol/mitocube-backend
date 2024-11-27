from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Self

import lib.data as dlib

class ABCTraitNotFoundError(dlib.ABCAttributeError):
    pass

class ABCTrait(ABC, dlib.FlexDataClass):
    def __init__(self, parent_attribute: dlib.ABCAttribute, tag: str, text: str,
                 keyword: str | None, description: str | None, db_id: int | None = None):
        self._id: int = db_id
        self._attribute: dlib.ABCAttribute = parent_attribute
        self._tag: str = tag
        self._text: str = text
        self._keyword: str | None = keyword
        self._description: str | None = description

    def __repr__(self):
        return "{}(id={}, tag={})".format(self.__class__.__name__, self._id, self.get_full_tag())

    @classmethod
    def _get_class_rulings(cls) -> Dict[str, Self]:  # ToDo: Update return values!
        import lib.data.sql.postgresql as sqllib
        return {"postgresql": sqllib.PostgreSQLTrait}

    @abstractmethod
    def add_to_dataset_id(self, dataset_id: int) -> dlib.ABCTraitNode:
        pass

    @abstractmethod
    def add_to_sample_id(self, sample_id: int) -> dlib.ABCTraitNode:
        pass

    @staticmethod
    @abstractmethod
    def does_tag_exist(attribute: dlib.ABCAttribute, tag: str) -> bool:
        pass

    @staticmethod
    @abstractmethod
    def get_all_traits(attributes: Dict[int, dlib.ABCAttribute] | None = None) -> Dict[id, ABCTrait]:
        pass

    @staticmethod
    @abstractmethod
    def is_keyword_taken(keyword: str) -> bool:
        pass

    def get_id(self) -> int | None:
        return self._id

    def get_attribute(self) -> dlib.ABCAttribute:
        return self._attribute

    def get_tag(self) -> str:
        return self._tag

    def get_full_tag(self) -> str:
        return "{attribute}:{trait}".format(attribute=self._attribute.get_tag(), trait = self._tag)

    def get_text(self) -> str:
        return self._text

    def get_keyword(self) -> str | None:
        return self._keyword

    def get_description(self) -> str | None:
        return self._description

    @classmethod
    @abstractmethod
    def objectify_with_id(cls, db_id: int) -> ABCTrait:
        pass

    @classmethod
    @abstractmethod
    def objectify_with_tag(cls, full_tag: str | None) -> ABCTrait:
        pass

    @classmethod
    @abstractmethod
    def objectify_with_keyword(cls, keyword: str) -> ABCTrait:
        pass

    def set(self, parent_attribute: dlib.ABCAttribute, tag: str, text: str, keyword: str | None, description: str | None):
        self._attribute = parent_attribute
        self._tag = tag
        self._text = text,
        self._keyword = keyword
        self._description = description

    def set_parent_attribute(self, parent_attribute: dlib.ABCAttribute):
        self._attribute = parent_attribute

    def set_tag(self, tag: str):
        self._tag = tag

    def set_text(self, text: str):
        self._text = text,

    def set_keyword(self, keyword: str | None):
        self._keyword = keyword

    def set_description(self, description: str | None):
        self._description = description

    @abstractmethod
    def write_to_db(self):
        pass

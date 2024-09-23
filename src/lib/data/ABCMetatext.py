from __future__ import annotations

from abc import ABC, abstractmethod

from typing import Dict, List, Self

import lib.data as dlib

class ABCMetatextError(dlib.ABCDatasetError):
    pass

class ABCMetatext(ABC, dlib.FlexDataClass):

    def __init__(self, tag: str, text: str, dataset_id: int | None = None):
        self._dataset_id: int | None = dataset_id
        self._tag: str = tag
        self._text: str = text

    @classmethod
    def _get_class_rulings(cls) -> Dict[str, Self]:
        import lib.data.sql.postgresql as sqllib
        return {"postgresql": sqllib.PostgreSQLMetatext}

    def get_dataset_id(self) -> int | None:
        return self._dataset_id

    def get_tag(self) -> str:
        return self._tag

    def get_text(self) -> str:
        return self._text

    @staticmethod
    @abstractmethod
    def is_tag_used(dataset_id: int, tag: str) -> bool:
        pass

    @classmethod
    @abstractmethod
    def objectify_with_dataset_id(cls, dataset_id: int) -> List[ABCMetatext]:
        pass

    @abstractmethod
    def read(self):
        pass

    def set(self, dataset_id: int | None, tag: str, text: str):
        self._dataset_id = dataset_id
        self._tag = tag
        self._text = text

    def set_dataset_id(self, dataset_id: int | None):
        self._dataset_id = dataset_id

    def set_tag(self, tag: str):
        self._tag = tag

    def set_text(self, text: str):
        self._text = text

    @abstractmethod
    def write(self):
        pass

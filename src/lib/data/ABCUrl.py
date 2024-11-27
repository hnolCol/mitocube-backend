from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Self

import lib.data as dlib

class ABCUrlError(dlib.ABCDatasetError):
    pass

class ABCUrl(ABC, dlib.FlexDataClass):

    def __init__(self, url: str, dataset_id: int | None = None):
        self._dataset_id: int | None = dataset_id
        self._url: str = url

    @classmethod
    def _get_class_rulings(cls) -> Dict[str, Self]:
        import lib.data.sql.postgresql as sqllib
        return {"postgresql": sqllib.PostgreSQLUrl}

    def get_dataset_id(self) -> int | None:
        return self._dataset_id

    def get_url(self) -> str:
        return self._url

    @abstractmethod
    def append_to_dataset(self, dataset_id: int | None = None):
        pass

    @classmethod
    @abstractmethod
    def objectify_with_dataset_id(cls, dataset_id: int) -> List[ABCUrl]:
        pass

    @classmethod
    @abstractmethod
    def remove_all_from_dataset(cls, dataset_id: int) :
        pass

    def set(self, dataset_id: int | None, url: str):
        self._dataset_id = dataset_id
        self._url = url

    def set_dataset_id(self, dataset_id: int | None):
        self._dataset_id = dataset_id

    def set_url(self, url: str):
        self._url = url


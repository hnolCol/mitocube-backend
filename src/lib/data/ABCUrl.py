from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Self

import lib.data as dlib

class ABCUrlError(dlib.ABCDatasetError):
    pass

class ABCUrl(ABC, dlib.FlexDataClass):

    def __init__(self, dataset_id: int, url: str):
        self._dataset_id: int = dataset_id
        self._url: str = url

    @classmethod
    def _get_class_rulings(cls) -> Dict[str, Self]:
        import lib.data.sql.postgresql as sqllib
        return {"postgresql": sqllib.PostgreSQLUrl}

    def get_dataset_id(self) -> int:
        return self._dataset_id

    def get_url(self) -> str:
        return self._url

    @abstractmethod
    def append_to_dataset(self):
        pass

    @classmethod
    @abstractmethod
    def objectify_with_dataset_id(cls, dataset_id: int) -> List[ABCUrl]:
        pass

    def set(self, dataset_id: int, url: str):
        self._dataset_id = dataset_id
        self._url = url

    def set_dataset_id(self, dataset_id: int):
        self._dataset_id = dataset_id

    def set_url(self, url: str):
        self._url = url


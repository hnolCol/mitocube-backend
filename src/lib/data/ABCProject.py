from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Self

import lib.data as dlib

class ABCProjectError(dlib.ABCDataError):
    pass

class ABCProject(ABC, dlib.FlexDataClass):

    def __init__(self, db_id: int | None, title: str, description: str | None, datasets: List[dlib.ABCDataset] | None = None):
        self._id: int = db_id
        self._title: str = title
        self._description: str | None = description

        self._datasets: List[dlib.ABCDataset] | None = datasets  # ToDo: add some loading methods and check how many exists

    @classmethod
    def _get_class_rulings(cls) -> Dict[str, Self]:
        import lib.data.sql.postgresql as sqllib
        return {"postgresql": sqllib.PostgreSQLProject}

    @abstractmethod
    def does_exist(self):
        pass

    @staticmethod
    @abstractmethod
    def does_exist_with_id(db_id: int) -> bool:
        pass

    def get_id(self) -> int | None:
        return self._id

    def get_title(self) -> str | None:
        return self._title

    def get_datasets(self) -> List[dlib.ABCDataset] | None:
        return self._datasets

    def get_description(self) -> str | None:
        return self._description

    @abstractmethod
    def read(self, fetch_datasets: bool = False):
        pass

    def set(self, db_id: int | None, title: str, description: str | None, datasets: List[dlib.ABCDataset] | None = None):
        self._id = db_id
        self._title = title
        self._description = description
        self._datasets = datasets

    def set_id(self, db_id: int | None):
        self._id: int = db_id

    def set_title(self, title: str):
        self._title: str = title

    def set_datasets(self, datasets: List[dlib.ABCDataset] | None = None):
        self._datasets: List[dlib.ABCDataset] | None = datasets

    def set_description(self, description: str | None):
        self._description: str | None = description

    @abstractmethod
    def write(self, write_datasets: bool = False):
        pass

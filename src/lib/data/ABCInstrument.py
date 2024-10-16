from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Self, List

import lib.data as dlib

class ABCInstrumentError(dlib.ABCDataError):
    pass

class ABCInstrument(ABC, dlib.FlexDataClass):
    def __init__(self, label: str, name: str, db_id: int | None = None,
                 location: str | None = None, description: str | None = None, base64_image: str | None = None):
        self._id: int | None = db_id
        self._label: str = label
        self._name: str = name
        self._location: str = location
        self._description: str | None = description
        self._base64_image: str | None = base64_image

    @classmethod
    def _get_class_rulings(cls) -> Dict[str, Self]:
        import lib.data.sql.postgresql as sqllib
        return {"postgresql": sqllib.PostgreSQLInstrument}

    @abstractmethod
    def does_exist(self):
        pass

    @staticmethod
    @abstractmethod
    def does_exist_with_id(db_id: int) -> bool:
        pass

    @staticmethod
    @abstractmethod
    def does_exist_with_label(label: str) -> bool:
        pass

    @staticmethod
    @abstractmethod
    def get_instruments(self) -> List[ABCInstrument]:
        pass

    def get_id(self) -> int | None:
        return self._id

    def get_label(self) -> str:
        return self._label

    def get_name(self) -> str:
        return self._name

    def get_location(self) -> str | None:
        return self._location

    def get_description(self) -> str | None:
        return self._description

    def get_base64_image(self) -> str | None:
        return self._base64_image

    @classmethod
    @abstractmethod
    def objectify_with_id(cls, db_id: int) -> dlib.ABCInstrument:
        pass

    @classmethod
    @abstractmethod
    def objectify_with_label(cls, label: str) -> dlib.ABCInstrument:
        pass

    @abstractmethod
    def read(self):
        pass

    def set(self, label: str, name: str, db_id: int | None = None , location: str | None = None, description: str | None = None, base64_image: str | None = None):
        self._id = db_id
        self._label = label
        self._name = name
        self._location = location
        self._description = description
        self._base64_image = base64_image

    def set_id(self, db_int: int | None):
        self._id = db_int

    def set_label(self, label: str):
        self._label = label

    def set_name(self, name: str):
        self._name = name

    def set_location(self, location: str | None) :
        self._location = location

    def set_description(self, description: str | None):
        self._description = description

    def set_base64_image(self, base64_image: str | None):
        self._base64_image = base64_image

    @abstractmethod
    def write(self):
        pass

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Self

import lib.data as dlib

class ABCProteomeError(dlib.ABCDatasetError):
    pass

class ABCProteome(ABC, dlib.FlexDataClass):

    def __init__(self, proteome_id: str,
                 organism: dlib.ABCOrganism,
                 db_id: int | None = None,
                 status: str | None = None,
                 comment: str | None = None):
        self._id: int | None = db_id
        self._proteome_id: str = proteome_id
        self._organism: dlib.ABCOrganism = organism
        self._status: str | None = status
        self._comment: str | None = comment

    @classmethod
    def _get_class_rulings(cls) -> Dict[str, Self]:
        import lib.data.sql.postgresql as sqllib
        return {"postgresql": sqllib.PostgreSQLUrl}

    def get_comment(self) -> str | None:
        return self._comment

    def get_id(self) -> int | None:
        return self._id

    def get_proteome_id(self) -> str:
        return self._proteome_id

    def get_organism(self) -> dlib.ABCOrganism:
        return self._organism

    def get_status(self) -> str | None:
        return self._status

    @classmethod
    @abstractmethod
    def objectify_with_id(cls, db_id: int) -> ABCProteome:
        pass

    @classmethod
    @abstractmethod
    def objectify_with_proteome_id(cls, proteome_id: str) -> ABCProteome:
        pass

    def set(self, proteome_id: str,
            organism: dlib.ABCOrganism,
            db_id: int | None = None,
            status: str | None = None,
            comment: str | None = None):
        self._id = db_id
        self._proteome_id = proteome_id
        self._organism = organism
        self._status = status
        self._comment = comment

    def set_comment(self, comment: str | None):
        self._comment = comment

    def set_id(self, db_id: int | None):
        self._id = db_id

    def set_proteome_id(self, proteome_id: str):
        self._proteome_id = proteome_id

    def set_organism(self, organism: dlib.ABCOrganism):
        self._organism = organism

    def set_status(self, status: str | None):
        self._status = status

    @abstractmethod
    def write_to_db(self):
        pass

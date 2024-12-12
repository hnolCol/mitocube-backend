from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Self

import lib.data as dlib

class ABCOrganismError(dlib.ABCDatasetError):
    pass

class ABCOrganism(ABC, dlib.FlexDataClass):

    def __init__(self, label: str, taxon_id: int, mnemonic_name: str, scientific_name: str,
                 common_name: str, phylum: str, db_id: int | None = None, description: str | None = None):
        self._db_id: int | None = db_id
        self._label: str = label
        self._taxon_id: int = taxon_id
        self._mnemonic_name: str = mnemonic_name
        self._scientific_name: str = scientific_name
        self._common_name: str = common_name
        self._phylum: str = phylum
        self._description: str = description

    @classmethod
    def _get_class_rulings(cls) -> Dict[str, Self]:
        import lib.data.sql.postgresql as sqllib
        return {"postgresql": sqllib.PostgreSQLUrl}

    def get_common_name(self) -> str:
        return self._common_name

    def get_description(self) -> str | None:
        return self._description

    def get_id(self) -> int | None:
        return self._db_id

    def get_label(self) -> str:
        return self._label

    def get_taxon_id(self) -> int:
        return self._taxon_id

    def get_mnemonic_name(self) -> str:
        return self._mnemonic_name

    def get_scientific_name(self) -> str:
        return self._scientific_name

    def get_phylum(self) -> str:
        return self._phylum

    @classmethod
    @abstractmethod
    def objectify_with_id(cls, db_id: int) -> ABCOrganism:
        pass

    @classmethod
    @abstractmethod
    def objectify_with_label(cls, label: str) -> ABCOrganism:
        pass

    def set(self, label: str, taxon_id: int, mnemonic_name: str, scientific_name: str,
                 common_name: str, phylum: str, db_id: int | None = None, description: str | None = None):
        self._db_id = db_id
        self._label = label
        self._taxon_id = taxon_id
        self._mnemonic_name = mnemonic_name
        self._scientific_name = scientific_name
        self._common_name = common_name
        self._phylum = phylum
        self._description = description

    def set_common_name(self, common_name: str):
        self._common_name = common_name

    def set_description(self, description: str | None):
        self._description = description

    def set_id(self, db_id: int | None):
        self._db_id = db_id

    def set_label(self, label: str):
        self._label = label

    def set_taxon_id(self, taxon_id: int):
        self._taxon_id = taxon_id

    def set_mnemonic_name(self, mnemonic_name: str):
        self._mnemonic_name = mnemonic_name

    def set_scientific_name(self, scientific_name: str):
        self._scientific_name = scientific_name

    def set_phylum(self, phylum: str):
        self._phylum = phylum

    @abstractmethod
    def write_to_db(self):
        pass

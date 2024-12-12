from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Self

import lib.data as dlib

class ABCFeatureError(dlib.ABCDatasetError):
    pass

class ABCFeature(ABC, dlib.FlexDataClass):

    def __init__(self, label: str, proteome: dlib.ABCProteome, organism: dlib.ABCOrganism,
                 gene_name: str | None, protein_name: str | None,
                 length_aa: int | None, mass: float | None, sequence: str | None, is_reviewed: bool,
                 db_id: int | None = None, is_grouped: bool = False):
        self._id: int | None = db_id
        self._label: str = label
        self._proteome: dlib.ABCProteome = proteome
        self._organism: dlib.ABCOrganism = organism
        self._is_grouped: bool = is_grouped
        self._gene_name: str | None = gene_name
        self._protein_name: str | None = protein_name
        self._length_aa: int | None = length_aa
        self._mass: float | None = mass
        self._sequence: str | None = sequence
        self._is_reviewed: bool = is_reviewed

    @classmethod
    def _get_class_rulings(cls) -> Dict[str, Self]:
        import lib.data.sql.postgresql as sqllib
        return {"postgresql": sqllib.PostgreSQLUrl}

    def get_id(self) -> int | None:
        return self._id

    def get_label(self) -> str:
        return self._label

    def get_proteome(self) -> dlib.ABCProteome:
        return self._proteome

    def get_organism(self) -> dlib.ABCOrganism:
        return self._organism

    def get_is_grouped(self) -> bool:
        return self._is_grouped

    def get_gene_name(self) -> str | None:
        return self._gene_name

    def get_protein_name(self) -> str | None:
        return self._protein_name

    def get_length_aa(self) -> int | None:
        return self._length_aa

    def get_mass(self) -> float | None:
        return self._mass

    def get_sequence(self) -> str | None:
        return self._sequence

    def get_is_reviewed(self) -> bool:
        return self._is_reviewed

    @classmethod
    @abstractmethod
    def objectify_with_id(cls, db_id: int) -> ABCFeature:
        pass

    @classmethod
    @abstractmethod
    def objectify_with_label(cls, label: str) -> ABCFeature:
        pass

    def set(self, label: str, proteome: dlib.ABCProteome, organism: dlib.ABCOrganism,
            gene_name: str | None, protein_name: str | None,
            length_aa: int | None, mass: float | None, sequence: str | None, is_reviewed: bool,
            db_id: int | None = None, is_grouped: bool = False):
        self._id = db_id
        self._label = label
        self._proteome = proteome
        self._organism = organism
        self._is_grouped = is_grouped
        self._gene_name = gene_name
        self._protein_name = protein_name
        self._length_aa = length_aa
        self._mass = mass
        self._sequence = sequence
        self._is_reviewed = is_reviewed

    def set_id(self, db_id: int | None):
        self._id = db_id

    def set_label(self, label: str):
        self._label = label

    def set_proteome(self, proteome: dlib.ABCProteome):
        self._proteome = proteome

    def set_organism(self, organism:  dlib.ABCOrganism):
        self._organism = organism

    def set_is_grouped(self, is_grouped: bool):
        self._is_grouped = is_grouped

    def set_gene_name(self, gene_name: str | None):
        self._gene_name = gene_name

    def set_protein_name(self, protein_name: str | None):
        self._protein_name = protein_name

    def set_length_aa(self, length_aa: int | None):
        self._length_aa = length_aa

    def set_mass(self, mass: float | None):
        self._mass = mass

    def set_sequence(self, sequence: str | None):
        self._sequence = sequence

    def set_is_reviewed(self, is_reviewed: bool):
        self._is_reviewed = is_reviewed

    @abstractmethod
    def write_to_db(self):
        pass

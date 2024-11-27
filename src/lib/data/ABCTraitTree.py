from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Self

import lib.data as dlib

class ABCTraitTreeError(dlib.ABCAttributeError):
    pass

class ABCTraitTreeNotFoundError(ABCTraitTreeError):
    pass


class ABCTraitTree(ABC, dlib.FlexDataClass):
    def __init__(self, root: dlib.ABCTraitNode):
        self._root: dlib.ABCTraitNode = root

    @classmethod
    def _get_class_rulings(cls) -> Dict[str, Self]:
        import lib.data.sql.postgresql as sqllib
        return {"postgresql": sqllib.PostgreSQLTraitTree}

    def get_root(self) -> dlib.ABCTraitNode:
        return self._root

    @staticmethod
    @abstractmethod
    def get_all_root_nodes() -> List[ABCTraitTree]:
        pass

    @staticmethod
    @abstractmethod
    def get_all_trees_with_children() -> List[ABCTraitTree]:
        pass

    @staticmethod
    @abstractmethod
    def query_tree_with_traits(traits: List[dlib.ABCTrait]) -> List[ABCTraitTree]:
        pass

    @staticmethod
    @abstractmethod
    def query_trees_with_label(search_term: str) -> List[ABCTraitTree]:
        pass

    @classmethod
    @abstractmethod
    def objectify_with_root_trait_node_id(cls, db_id: int) -> ABCTraitTree:
        pass

    @classmethod
    @abstractmethod
    def objectify_with_dataset_id(cls, db_id: int) -> List[ABCTraitTree]:
        pass

    @classmethod
    @abstractmethod
    def objectify_with_dataset_label(cls, label: str) -> List[ABCTraitTree]:
        pass

    @classmethod
    @abstractmethod
    def objectify_with_sample_id(cls, sample_id: int) -> List[ABCTraitTree]:
        pass

    @classmethod
    @abstractmethod
    def objectify_with_sample_label(cls, dataset_id: int, label: str) -> List[ABCTraitTree]:
        pass

    @abstractmethod
    def write_to_db(self):
        pass

    @abstractmethod
    def remove_from_db(self):
        pass

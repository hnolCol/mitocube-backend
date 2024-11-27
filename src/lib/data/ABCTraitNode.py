from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Self

import lib.data as dlib

class ABCTraitNodeError(dlib.ABCAttributeError):
    pass

class ABCTraitNodeNotFoundError(ABCTraitNodeError):
    pass

class ABCTraitNode(ABC, dlib.FlexDataClass):

    def __init__(self, trait: dlib.ABCTrait,
                 db_id: int | None = None,
                 parent_node: ABCTraitNode | None = None,
                 child_nodes: List[ABCTraitNode] | None = None,
                 name: str | None = None,
                 value: str | None = None):
        self._id: int | None = db_id
        self._parent_node: ABCTraitNode | None = parent_node
        self._child_nodes: List[ABCTraitNode] | None = child_nodes
        self._trait: dlib.ABCTrait = trait
        self._name: str | None = name
        self._value: str | None = value

    @classmethod
    def _get_class_rulings(cls) -> Dict[str, Self]:
        import lib.data.sql.postgresql as sqllib
        return {"postgresql": sqllib.PostgreSQLABCTraitNode}

    def get_id(self) -> int | None:
        return self._id

    def get_full_tag(self) -> str:
        if self._value:
            return "{tag}({value})".format(tag = self._trait.get_full_tag(), value = self._value)
        else:
            return self._trait.get_full_tag()

    def get_trait(self) -> dlib.ABCTrait:
        return self._trait

    def get_name(self) -> str | None:
        return self._name

    def get_parent(self) -> ABCTraitNode | None:
        return self._parent_node

    def get_children(self) -> List[ABCTraitNode] | None:
        return self._child_nodes

    def get_value(self) -> str | None:
        return self._value

    def set(self, trait: dlib.ABCTrait, name: str | None = None, value: str | None = None):
        self._trait = trait
        self._name = name
        self._value = value

    def set_parent_node(self, parent_node: ABCTraitNode | None):
        self._parent_node = parent_node

    def add_child(self, child: ABCTraitNode):
        if self._child_nodes is None:
            self._child_nodes = []

        self._child_nodes.append(child)

        if child.get_parent() is None:
            child.set_parent_node(parent_node=self)
        elif child.get_parent() is not self:
            raise ABCTraitNodeError("The child has already a parent not that is not the current object!")

    def remove_child(self, child: ABCTraitNode):
        if self._child_nodes is None:
            raise ABCTraitNodeError("The node does not have any children!")

        if child.get_parent():
            if child.get_parent() is not self:
                raise ABCTraitNodeError("The node is not the parent of the child!")
            child.set_parent_node(parent_node=None)

        if child not in self._child_nodes:
            raise ABCTraitNodeError("The child is not part of the children of the node!")

        child.set_parent_node(parent_node=None)
        self._child_nodes.remove(child)

        if len(self._child_nodes) < 1:
            self._child_nodes = None

    def set_child_nodes(self, child_nodes: List[ABCTraitNode] | None):
        self._child_nodes = child_nodes

    def set_name(self, name: str | None = None):
        self._name = name

    def set_value(self, value: str | None = None):
        self._value = value

    @abstractmethod
    def add_to_dataset_id(self, dataset_id: int):
        pass

    @abstractmethod
    def add_to_sample_id(self, sample_id: int):
        pass

    @abstractmethod
    def remove_from_dataset_id(self, dataset_id: int):
        pass

    @abstractmethod
    def remove_from_sample_id(self, sample_id: int):
        pass

    @abstractmethod
    def write_to_db(self):
        pass

    @abstractmethod
    def remove_from_db(self):
        pass

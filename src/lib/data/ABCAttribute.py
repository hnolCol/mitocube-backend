from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Self

import lib.data as dlib

class ABCAttributeError(dlib.ABCDataError):
    pass

class ABCAttributeNotFoundError(ABCAttributeError):
    pass

class ABCAttribute(ABC, dlib.FlexDataClass):
    def __init__(self, parent_attribute: ABCAttribute | None, tag: str, text: str | None,
                 db_id: int | None = None,
                 priority: int = 500,
                 required_for_dataset_state: dlib.DatasetState = dlib.DatasetState.INITIALISED,
                 allow_as_filter: bool = True,
                 allow_for_dataset: bool = True,
                 allow_for_genotype: bool = True,
                 allow_for_performance: bool = True,
                 allow_for_sample: bool = True,
                 allow_trait_values: bool = True,
                 values_are_numeric: bool = True,
                 values_are_feature_labels: bool = True):

        self._id: int = db_id
        self._parent: ABCAttribute | None = parent_attribute
        self._tag: str = tag
        self._text: str = text
        self._priority: int = priority

        self._allow_as_filter: bool = allow_as_filter
        self._allow_for_dataset: bool = allow_for_dataset
        self._allow_for_sample: bool = allow_for_sample
        self._allow_for_genotype: bool = allow_for_genotype
        self._allow_for_performance: bool = allow_for_performance

        self._allow_trait_values: bool = allow_trait_values
        self._values_are_numeric: bool = values_are_numeric
        self._values_are_feature_labels: bool = values_are_feature_labels

        self._required_for_dataset_state: dlib.DatasetState = required_for_dataset_state

    def __repr__(self):
        return "{}(id={}, tag={})".format(self.__class__.__name__, self._id, self._tag)

    @classmethod
    def _get_class_rulings(cls) -> Dict[str, Self]:  # ToDo: Update return values!
        import lib.data.sql.postgresql as sqllib
        return {"postgresql": sqllib.PostgreSQLAttribute}

    def allowed_as_filter(self) -> bool:
        return self._allow_as_filter

    def allowed_for_samples(self) -> bool:
        return self._allow_for_sample

    def allowed_for_datasets(self) -> bool:
        return self._allow_for_dataset

    def allowed_for_genotypes(self) -> bool:
        return self._allow_for_genotype

    def allowed_for_performance(self) -> bool:
        return self._allow_for_performance

    def are_trait_values_allowed(self) -> bool:
        return self._allow_trait_values

    def are_values_numeric(self) -> bool:
        return self._values_are_numeric

    def are_values_features(self) -> bool:
        return self._values_are_feature_labels

    @staticmethod
    @abstractmethod
    def does_tag_exist(tag: str) -> bool:
        pass

    @staticmethod
    @abstractmethod
    def get_all_attributes() -> Dict[id, ABCAttribute]:
        pass

    def get_id(self) -> int | None:
        return self._id

    def get_parent_attribute(self) -> ABCAttribute | None:
        return self._parent

    def get_tag(self) -> str:
        return self._tag

    def get_text(self) -> str | None:
        return self._text

    def get_priority(self) -> int:
        return self._priority

    def get_required_for_dataset_state(self) -> dlib.DatasetState:
        return self._required_for_dataset_state

    @classmethod
    @abstractmethod
    def objectify_with_id(cls, db_id: int) -> ABCAttribute:
        pass

    @classmethod
    @abstractmethod
    def objectify_with_tag(cls, tag: str) -> ABCAttribute:
        pass

    def set(self, parent: ABCAttribute | None, tag: str, text: str | None, priority: int,
            required_for_dataset_state: dlib.DatasetState,
            allow_as_filter: bool, allow_for_dataset: bool, allow_for_genotype: bool, allow_for_performance: bool, allow_for_sample: bool,
            allow_trait_values: bool, values_are_numeric: bool, values_are_feature_labels: bool):
        self._parent = parent
        self._tag = tag
        self._text = text
        self._priority = priority
        self._required_for_dataset_state = required_for_dataset_state

        self._allow_as_filter = allow_as_filter
        self._allow_for_dataset = allow_for_dataset
        self._allow_for_genotype = allow_for_genotype
        self._allow_for_performance = allow_for_performance
        self._allow_for_sample = allow_for_sample

        self._allow_trait_values = allow_trait_values
        self._values_are_numeric = values_are_numeric
        self._values_are_feature_labels = values_are_feature_labels

    def set_permissions(self, required_for_dataset_state: dlib.DatasetState,
                        allow_as_filter: bool, allow_for_dataset: bool, allow_for_genotype: bool,
                        allow_for_performance: bool, allow_for_sample: bool, allow_trait_values: bool,
                        values_are_numeric: bool, values_are_feature_labels: bool):
        self._required_for_dataset_state = required_for_dataset_state

        self._allow_as_filter = allow_as_filter
        self._allow_for_dataset = allow_for_dataset
        self._allow_for_genotype = allow_for_genotype
        self._allow_for_performance = allow_for_performance
        self._allow_for_sample = allow_for_sample

        self._allow_trait_values = allow_trait_values
        self._values_are_numeric = values_are_numeric
        self._values_are_feature_labels = values_are_feature_labels

    def set_allow_as_filter(self, allow_as_filter: bool):
        self._allow_as_filter = allow_as_filter

    def set_allow_for_dataset(self, allow_for_dataset: bool):
        self._allow_for_dataset = allow_for_dataset

    def set_allow_for_genotype(self, allow_for_genotype: bool):
        self._allow_for_genotype = allow_for_genotype

    def set_allow_for_performance(self, allow_for_performance: bool):
        self._allow_for_performance = allow_for_performance

    def set_allow_for_sample(self, allow_for_sample: bool):
        self._allow_for_sample = allow_for_sample

    def set_allow_trait_values(self, allow_trait_values: bool):
        self._allow_trait_values = allow_trait_values

    def set_values_are_numeric(self, values_are_numeric: bool):
        self._values_are_numeric = values_are_numeric

    def set_values_are_feature_labels(self, values_are_feature_labels: bool):
        self._values_are_feature_labels = values_are_feature_labels

    def set_parent(self, parent: ABCAttribute):
        self._parent = parent

    def set_tag(self, tag: str):
        self._tag = tag

    def set_text(self, text: str | None):
        self._text = text

    def set_priority(self, priority: int):
        self._priority = priority

    def set_required_dataset_state(self, required_for_dataset_state: dlib.DatasetState):
        self._required_for_dataset_state = required_for_dataset_state

    @abstractmethod
    def write_to_db(self):
        pass


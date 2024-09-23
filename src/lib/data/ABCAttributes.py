from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Self

import lib.data as dlib

class ABCAttributeError(dlib.ABCDataError):
    pass


class ABCAttribute(ABC, dlib.FlexDataClass):
    def __init__(self, parent_attribute: ABCAttribute, tag: str, text: str | None, priority: int = 500, db_id: int | None = None,
                 allow_as_filter: bool = True, allow_for_dataset: bool = True, allow_for_genotype: bool = True,
                 allow_for_performance: bool = True, allow_for_sample: bool = True, allow_trait_values: bool = True,
                 required_for_dataset_state: dlib.DatasetState = dlib.DatasetState.INITIALISED):
        self._id: int = db_id
        self._parent: ABCAttribute | None = parent_attribute
        self._tag: str = tag
        self._text: str = text
        self._priority: int = priority
        self._allow_as_filter: bool = allow_as_filter
        self._allow_for_dataset: bool = allow_for_dataset
        self._allow_for_genotype: bool = allow_for_genotype
        self._allow_for_performance: bool = allow_for_performance
        self._allow_for_sample: bool = allow_for_sample
        self._allow_trait_values: bool = allow_trait_values
        self._required_for_dataset_state: dlib.DatasetState = required_for_dataset_state

    @classmethod
    def _get_class_rulings(cls) -> Dict[str, Self]:  # ToDo: Update return values!
        import lib.data.sql.postgresql as sqllib
        return {"postgresql": sqllib.PostgreSQLAttribute}

    def allowed_as_filter(self) -> bool:
        return self._allow_as_filter

    def allowed_for_datasets(self) -> bool:
        return self._allow_for_dataset

    def allowed_for_genotypes(self) -> bool:
        return self._allow_for_genotype

    def allowed_for_performance(self) -> bool:
        return self._allow_for_performance

    def allowed_for_samples(self) -> bool:
        return self._allow_for_sample

    def are_trait_values_allowed(self) -> bool:
        return self._allow_trait_values

    @staticmethod
    @abstractmethod
    def does_tag_exist(tag: str) -> bool:
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

    def set(self, parent: ABCAttribute, tag: str, text: str | None, priority: int, allow_as_filter: bool,
            allow_for_dataset: bool, allow_for_genotype: bool, allow_for_performance: bool, allow_for_sample: bool,
            allow_trait_values: bool, required_for_dataset_state: dlib.DatasetState):
        self._parent = parent
        self._tag = tag
        self._text = text
        self._priority = priority
        self._allow_as_filter = allow_as_filter
        self._allow_for_dataset = allow_for_dataset
        self._allow_for_genotype = allow_for_genotype
        self._allow_for_performance = allow_for_performance
        self._allow_for_sample = allow_for_sample
        self._allow_trait_values = allow_trait_values
        self._required_for_dataset_state = required_for_dataset_state

    def set_permissions(self,  allow_as_filter: bool, allow_for_dataset: bool, allow_for_genotype: bool,
                        allow_for_performance: bool, allow_for_sample: bool, allow_trait_values: bool,
                        required_for_dataset_state: dlib.DatasetState):
        self._allow_as_filter = allow_as_filter
        self._allow_for_dataset = allow_for_dataset
        self._allow_for_genotype = allow_for_genotype
        self._allow_for_performance = allow_for_performance
        self._allow_for_sample = allow_for_sample
        self._allow_trait_values = allow_trait_values
        self._required_for_dataset_state = required_for_dataset_state

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
    def read(self):
        pass

    @abstractmethod
    def write(self):
        pass


class ABCTrait(ABC, dlib.FlexDataClass):
    def __init__(self, parent_attribute: ABCAttribute, tag: str, text: str, keyword: str | None, description: str | None, db_id: int | None = None):
        self._id: int = db_id
        self._attribute: ABCAttribute = parent_attribute
        self._tag: str = tag
        self._text: str = text  # Fixme: issue with type. is text reserved?
        self._keyword: str | None = keyword
        self._description: str | None = description

    @classmethod
    def _get_class_rulings(cls) -> Dict[str, Self]:  # ToDo: Update return values!
        import lib.data.sql.postgresql as sqllib
        return {"postgresql": sqllib.PostgreSQLTrait}

    @staticmethod
    @abstractmethod
    def does_tag_exist(attribute: dlib.ABCAttribute, tag: str) -> bool:
        pass

    @staticmethod
    @abstractmethod
    def is_keyword_taken(keyword: str) -> bool:
        pass

    def get_id(self) -> int | None:
        return self._id

    def get_attribute(self) -> ABCAttribute:
        return self._attribute

    def get_tag(self) -> str:
        return self._tag

    def get_full_tag(self) -> str:
        return "{attribute}:{trait}".format(attribute=self._attribute.get_tag(), trait = self._tag)

    def get_text(self) -> str:
        return self._text

    def get_keyword(self) -> str | None:
        return self._keyword

    def get_description(self) -> str | None:
        return self._description

    @classmethod
    @abstractmethod
    def objectify_with_attribute_id(cls, db_id: int) -> Dict[str, ABCTrait]:
        pass

    @classmethod
    @abstractmethod
    def objectify_with_attribute_tag(cls, tag: str) -> Dict[str, ABCTrait]:
        pass

    @classmethod
    @abstractmethod
    def objectify_with_id(cls, db_id: int) -> ABCTrait:
        pass

    @classmethod
    @abstractmethod
    def objectify_with_tag(cls, full_tag: str | None) -> ABCTrait:
        pass

    @classmethod
    @abstractmethod
    def objectify_with_keyword(cls, keyword: str) -> ABCTrait:
        pass

    def set(self, parent_attribute: ABCAttribute, tag: str, text: str, keyword: str | None, description: str | None):
        self._attribute = parent_attribute
        self._tag = tag
        self._text = text,
        self._keyword = keyword
        self._description = description

    def set_parent_attribute(self, parent_attribute: ABCAttribute):
        self._attribute = parent_attribute

    def set_tag(self, tag: str):
        self._tag = tag

    def set_text(self, text: str):
        self._text = text,

    def set_keyword(self, keyword: str | None):
        self._keyword = keyword

    def set_description(self, description: str | None):
        self._description = description

    @abstractmethod
    def read(self):
        pass

    @abstractmethod
    def write(self):
        pass


class ABCTraitValue(ABC, dlib.FlexDataClass):

    def __init__(self, trait: dlib.ABCTrait, value: str | None = None, unit: str | None = None):
        self._trait: dlib.ABCTrait = trait
        self._value: str | None = value
        self._unit: str | None = unit

    @classmethod
    def _get_class_rulings(cls) -> Dict[str, Self]:
        import lib.data.sql.postgresql as sqllib
        return {"postgresql": sqllib.PostgreSQLTraitValue}

    def get_trait(self) -> dlib.ABCTrait:
        return self._trait

    def get_value(self) -> str | None:
        return self._value

    def get_unit(self) -> str | None:
        return self._unit

    def set(self, trait: dlib.ABCTrait, value: str | None = None, unit: str | None = None):
        self._trait: dlib.ABCTrait = trait
        self._value: str | None = value
        self._unit: str | None = unit

    @abstractmethod
    def add_to_dataset_id(self, dataset_id: int) -> List[ABCTraitValue]:
        pass

    @abstractmethod
    def add_to_sample_id(self, sample_id: int) -> List[ABCTraitValue]:
        pass

    @abstractmethod
    def remove_from_dataset_id(self, dataset_id: int):
        pass

    @abstractmethod
    def remove_from_sample_id(self, sample_id: int):
        pass

    @classmethod
    @abstractmethod
    def objectify_with_dataset_id(cls, db_id: int) -> List[ABCTraitValue]:
        pass

    @classmethod
    @abstractmethod
    def objectify_with_dataset_label(cls, label: str) -> List[ABCTraitValue]:
        pass

    @classmethod
    @abstractmethod
    def objectify_with_sample_id(cls, sample_id: int) -> List[ABCTraitValue]:
        pass

    @classmethod
    @abstractmethod
    def objectify_with_sample_label(cls, dataset_id: int, label: str) -> List[ABCTraitValue]:
        pass

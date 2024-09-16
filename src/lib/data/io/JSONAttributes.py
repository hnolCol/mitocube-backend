from __future__ import annotations

from datetime import datetime
import json
import re
from typing import Dict, List

import lib.data as dlib
import lib.data.sql.postgresql as psql
from lib.data import ABCAttribute


class JSONAttributes:

    def __init__(self, path_json_file: str, attribute_class: dlib.ABCAttribute = psql.PostgreSQLAttribute,
                 trait_class: dlib.ABCTrait = psql.PostgreSQLTrait):
        self._path_json_file: str = path_json_file

        self._attribute_class: dlib.ABCAttribute = attribute_class
        self._trait_class: dlib.ABCTrait = trait_class

        self._attributes: Dict[str, dlib.ABCAttribute] = {}
        self._attributes_sorted: List[dlib.ABCAttribute] = []

        self._traits: Dict[str, dlib.ABCTrait] = {}
        self._traits_sorted: List[dlib.ABCTrait] = []

    @staticmethod
    def __read_json(path: str) -> Dict[str, any]:
        with open(path, "r+") as io_in:
            return json.load(io_in)

    def read(self, ignore_missing_parent_attributes: bool = False):
        json_data = JSONAttributes.__read_json(path = self._path_json_file)

        subsequent_parents: Dict[str, str] = {}

        for json_attribute in json_data["attributes"]:
            if json_attribute["tag"] in self._attributes.keys():
                raise dlib.ABCAttributeError("Found duplicate for the attribute '{tag}'. Remove duplicates and start again!".format(tag=json_attribute["tag"]))

            if re.search("^att_[\w]+$", str(json_attribute["tag"])) is None:  # Fixme, change print to log or exception!
                print("Attribute with the tag '{tag}' is not allowed due to illegal characters or beginning. Skipping!".format(tag = json_attribute["tag"]))
                continue

            self._attributes[json_attribute["tag"]] = self._attribute_class(parent_attribute = None,
                                                                            tag = json_attribute["tag"],
                                                                            text = json_attribute["text"],
                                                                            priority = json_attribute["priority"],
                                                                            db_id = None,
                                                                            allow_as_filter = json_attribute["allow_as_filter"],
                                                                            allow_for_dataset = json_attribute["allow_for_dataset"],
                                                                            allow_for_genotype = json_attribute["allow_for_genotype"],
                                                                            allow_for_performance = json_attribute["allow_for_qc"],
                                                                            allow_for_sample = json_attribute["allow_for_sample"],
                                                                            allow_trait_values = json_attribute["has_numeric_input"],
                                                                            required_for_dataset_state = json_attribute["min_state"])  #: dlib.DatasetState = dlib.DatasetState.INITIALISED

            self._attributes_sorted.append(self._attributes[json_attribute["tag"]])

            if json_attribute["parent_tag"] is not None:
                subsequent_parents[json_attribute["tag"]] = json_attribute["parent_tag"]

        for child_tag, parent_tag in subsequent_parents.items():
            if parent_tag in self._attributes.keys():
                self._attributes[child_tag].set_parent(self._attributes[parent_tag])
            else:
                if not ignore_missing_parent_attributes:
                    raise dlib.ABCAttributeError("Parent '{parent}' cannot be added to '{child}' since the parent does not exist!".format(parent = parent_tag, child = child_tag))


        for json_trait in json_data["traits"] if "traits" in json_data.keys() else json_data["attribute_values"]:
            # dict_keys(['value', 'attribute_tag', 'attribute_id', 'id'])

            if re.search("^[\w]+$", str(json_trait["value"])) is None:  # Fixme, change print to log or exception!
                print("Trait with the tag '{trait}' ({attribute}:{trait}) is not allowed due to illegal characters. Skipping!".format(trait = json_trait["value"], attribute = json_trait["attribute_tag"]))
                continue

            combined_tag = "{attribute}:{trait}".format(attribute = json_trait["attribute_tag"], trait = json_trait["value"])


            if combined_tag in self._traits.keys():
                raise dlib.ABCAttributeError("Found duplicate for the trait '{tag}'. Remove duplicates and start again!".format(tag = combined_tag))

            self._traits[combined_tag] = self._trait_class(parent_attribute = self._attributes[json_trait["attribute_tag"]],
                                                           tag = str(json_trait["value"]),
                                                           text = json_trait["text"],
                                                           keyword = json_trait["keyword"],
                                                           description = json_trait["description"],
                                                           db_id = None)

            self._traits_sorted.append(self._traits[combined_tag])

    def write(self):
        for attribute in self._attributes_sorted:
            if not self._attribute_class.does_tag_exist(attribute.get_tag()):
                attribute.write()
            else:
                attribute.read()

        for trait in self._traits_sorted:
            if not self._trait_class.does_tag_exist(attribute = trait.get_attribute(), tag = trait.get_tag()):
                trait.write()
            else:
                trait.read()

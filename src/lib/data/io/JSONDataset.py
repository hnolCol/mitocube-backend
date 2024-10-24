from __future__ import annotations

from datetime import datetime
import json
from typing import Dict, Type, List

import lib.data as dlib
import lib.data.sql.postgresql as psql


class JSONDataset(dlib.ABCDataset):

    def __init__(self, path_json_file: str, external_id: str | None, state: dlib.DatasetState, title: str,
                 owner_user: dlib.ABCUser, contact_email: str, internal_id: int | None = None,
                 data: dlib.ABCDataTable | None = None, parent_project: dlib.ABCProject | None = None,
                 instrument: dlib.ABCInstrument | None = None, created_on: datetime | None = None,
                 uploaded_on: datetime | None = None, owner_group: dlib.ABCResearchGroup | None = None,
                 metatexts: Dict[str, dlib.ABCMetatext] = None, urls: List[dlib.ABCUrl] = None,
                 # attributes: Dict[str, dlib.ABCTrait] | None = None,
                 trait_values: Dict[str, dlib.ABCTraitValue] | None = None,
                 class_target: Type[dlib.ABCDataset] = psql.PostgreSQLDataset):

        super().__init__(external_id, state, title, owner_user, contact_email, internal_id, data, parent_project,
                         instrument, created_on, uploaded_on, owner_group, metatexts, urls, trait_values)

        self._path_json_file: str = path_json_file
        self._class_target: Type[dlib.ABCDataset] | None = class_target

        self._object_target: dlib.ABCDataset = class_target(external_id, state, title, owner_user,
                                                            contact_email, internal_id, data, parent_project,
                                                            instrument, created_on, uploaded_on, owner_group,
                                                            metatexts, urls, trait_values)

    @staticmethod
    def __read_json(path: str) -> Dict[str, any]:
        with open(path, "r+") as io_in:
            return json.load(io_in)

    def get_target_class(self) -> dlib.ABCDataset | None:  # ToDo: Fix Typing?
        return self._class_target

    def get_target_object(self) -> dlib.ABCDataset:
        return self._object_target

    def does_exist(self):
        pass

    @staticmethod
    def does_exist_with_id(db_id: int) -> bool:
        return False

    @staticmethod
    def does_exist_with_label(label: str) -> bool:
        return False

    @staticmethod
    def does_exist_with_labels(labels: List[str]) -> Dict[str, bool]:
        return {key: False for key in labels}

    @staticmethod
    def get_full_dataset_list() -> Dict[str, int]:
        raise dlib.ABCDatasetError("JSONDataset does not support database and has no permament dataset storage implemented.")

    @classmethod
    def objectify_with_id(cls, db_id: int) -> dlib.ABCDataset:
        raise dlib.ABCDatasetError("Objectify methods using ids are not implemented (possible) for the class JSON Dataset.")

    @classmethod
    def objectify_with_label(cls, label: str) -> dlib.ABCDataset:
        raise dlib.ABCDatasetError("Objectify methods using labels are not implemented (possible) for the class JSON Dataset.")

    @classmethod
    def objectify_with_dataset(cls, dataset: dlib.ABCDataset) -> dlib.ABCDataset:
        raise dlib.ABCDatasetError("Objectify methods using other datasets are not implemented (possible) for the class JSON Dataset.")

    @classmethod
    def objectify_with_json(cls, path: str, owner_user: dlib.ABCUser, owner_group: dlib.ABCResearchGroup | None = None,
                            data_table: dlib.ABCDataTable | None = None,
                            class_target: Type[dlib.ABCDataset] = psql.PostgreSQLDataset,
                            class_attribute_trait: Type[dlib.ABCTrait] = psql.PostgreSQLTrait,
                            class_attribute_trait_value: Type[dlib.ABCTraitValue] = psql.PostgreSQLTrait):
        data = JSONDataset.__read_json(path)

        trait_values_dataset = {}

        if "dataset_attributes" in data:
            for key, values in data["dataset_attributes"].items():
                for item in values:
                    try:
                        # Question, How are values currently saved?
                        trait_values_dataset[item] = class_attribute_trait_value(trait = class_attribute_trait.objectify_with_tag(full_tag = item), value=None)
                        # traits_dataset.append(class_attribute_traits.objectify_with_tag(full_tag = item))
                    except Exception as err:
                        print("Unable to catch for dataset: {} = {} \t {}".format(key, item, err))  # Question: How to print warnings? Or stop here?

        if "samples_attributes" in data:
            if data_table is not None:
                # index attributes: att_key = [0, 1, 2, 3]

                cleaned_trait_values: Dict[str, List[class_attribute_trait_value]] = {}
                collected_traits: Dict[str, class_attribute_trait] = {}

                for att, items in data["samples_attributes"].items():
                    for trait_key, ixs in items.items():
                        try:
                            if trait_key in collected_traits:
                                trait = collected_traits[trait_key]
                            else:
                                trait = class_attribute_trait.objectify_with_tag(full_tag = trait_key)
                                collected_traits[trait_key] = trait

                            for ix in ixs:
                                trait_value = class_attribute_trait_value(trait=trait, value=None, unit=None)

                                if data["sample_names"][ix] not in cleaned_trait_values:
                                    cleaned_trait_values[data["sample_names"][ix]] = []

                                cleaned_trait_values[data["sample_names"][ix]].append(trait_value)

                        except dlib.ABCAttributeError as err:
                            print("Error: Issue with {}, skipping! - {}".format(trait_key, err))

                data_table.set_samples_attributes(cleaned_trait_values)

        if "replicates" in data:
            if data_table is not None:
                # Assign replicates
                # Just a list? same order as samples? with repeating numbers replicates?
                replicates_samples: Dict[str, str] = {}
                for ix, item in enumerate(data["sample_names"]):
                    replicates_samples[item] = str(data["replicates"][ix])
                data_table.set_samples_replicates(replicates=replicates_samples)

        if "batches" in data:
            if data_table is not None:
                # Assign replicates
                # Just a list? same order as samples? with repeating numbers replicates?
                batches_samples: Dict[str, str] = {}
                for ix, item in enumerate(data["sample_names"]):
                    batches_samples[item] = str(data["batches"][ix])
                data_table.set_samples_batches(batches=batches_samples)

        dataset = cls(path_json_file = path, internal_id = None, external_id = data["label"],
                      data = data_table, parent_project = None, instrument = None,
                      created_on = datetime.fromtimestamp(data["created_on"]),  # ToDo: To int to date
                      uploaded_on = None,  # ToDo: Figure out
                      state = data["state"],  # ToDo:  dlib.DatasetState  # ToDo: "state" 5 ?
                      title = data["title"],
                      owner_user = owner_user,  # ToDo: Fix Class selection
                      owner_group = owner_group,  # ToDo: Fix Class selection
                      contact_email = data["title"],
                      metatexts = {k.replace("metatext:", ""): dlib.ABCMetatext.get_class()(tag = k.replace("metatext:", ""), text = v) for k, v in data["metatext"].items()},  # ToDo: Fix Class selection
                      urls = None if data["links"] is None or len(data["links"]) < 1 else data["links"],  # ToDo: Fix Class selection
                      trait_values = trait_values_dataset,
                      class_target = class_target)

        return dataset

    def read(self, fetch_datatable: bool = False):  # ToDo: Implement Exception?
        pass

    def update_state(self, state: dlib.DatasetState | None, allow_downgrade: bool = False):  # ToDo: Implement Exception?
        pass

    def write(self, write_datatable: bool = False):
        raise dlib.ABCDatasetError("JSONDataset is read only!")

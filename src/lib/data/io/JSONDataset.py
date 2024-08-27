from __future__ import annotations

from datetime import datetime
import json
from typing import Dict, List

import lib.data as dlib
from lib.data import DatasetState


class JSONDataset(dlib.ABCDataset):



    def __init__(self, path_json_file: str, external_id: str | None, state: DatasetState, title: str,
                 owner_user: dlib.ABCUser, contact_email: str, internal_id: int | None = None,
                 data: dlib.ABCDataTable | None = None, parent_project: dlib.ABCProject | None = None,
                 instrument: dlib.ABCInstrument | None = None, created_on: datetime | None = None,
                 uploaded_on: datetime | None = None, owner_group: dlib.ABCResearchGroup | None = None,
                 metatexts: Dict[str, dlib.ABCMetatext] = None, urls: List[dlib.ABCUrl] = None):

        super().__init__(external_id, state, title, owner_user, contact_email, internal_id, data, parent_project,
                         instrument, created_on, uploaded_on, owner_group, metatexts, urls)

        self._path_json_file: str = path_json_file

    @staticmethod
    def __read_json(path: str) -> Dict[str, any]:
        with open(path, "r+") as io_in:
            return json.load(io_in)

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

    @classmethod
    def objectify_with_id(cls, db_id: int) -> dlib.ABCDataset:
        raise dlib.ABCDatasetError("Objectify methods using ids are not implemented (possible) for the class JSON Dataset.")

    @classmethod
    def objectify_with_label(cls, label: str) -> dlib.ABCDataset:
        raise dlib.ABCDatasetError("Objectify methods using labels are not implemented (possible) for the class JSON Dataset.")

    @classmethod
    def objectify_with_json(cls, path: str, owner_user: dlib.ABCUser, owner_group: dlib.ABCResearchGroup | None = None):
        data = JSONDataset.__read_json(path)

        dataset = cls(path_json_file = path, internal_id = None, external_id = data["label"],
                      data = None, parent_project = None, instrument = None,
                      created_on = datetime.fromtimestamp(data["created_on"]),  # ToDo: To int to date
                      uploaded_on = None,  # ToDo: Figure out
                      state = data["state"],  # ToDo:  dlib.DatasetState  # ToDo: "state" 5 ?
                      title = data["title"],
                      owner_user = owner_user,
                      owner_group = owner_group,
                      contact_email = data["title"],
                      metatexts = {k.replace("metatext:", ""): dlib.ABCMetatext.get_class()(tag = k.replace("metatext:", ""), text = v) for k, v in data["metatext"].items()},
                      urls = None if data["links"] is None or len(data["links"]) < 1 else data["links"]  # urls: List[dlib.ABCUrl]
                      )

        return dataset


    def read(self, fetch_datatable: bool = False):
        pass

    def update_state(self, state: DatasetState | None, allow_downgrade: bool = False):
        pass

    def write(self):
        raise dlib.ABCDatasetError("JSONDataset is read only!")


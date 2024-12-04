from __future__ import annotations

from abc import ABC, ABCMeta, abstractmethod
from datetime import datetime
from enum import IntEnum, unique
from typing import Dict, List, Self, Type

import lib.data as dlib

from config import get_system_settings

@unique
class DatasetState(IntEnum):
    """
    Enums that are defined in the frontend which
    knows what to do with such input types.
    """
    INACTIVE = -50  # set to -100?
    CANCELED = -20
    PAUSED = -10
    INITIALISED = 0
    PROCESSED = 10
    MEASURING = 20
    UPLOADED = 25
    ANALYSIS = 30
    DONE = 40   # set to 50?
    ACTIVE = 50  # set to 100?  # before only dataset meta information is visible


class ABCDatasetError(dlib.ABCDataError):
    pass


class ABCDatasetNotFoundError(ABCDatasetError):
    pass


class ABCDataset(ABC, dlib.FlexDataClass):
    def __init__(self, external_id: str | None, state: DatasetState, title: str, owner_user: dlib.ABCUser,
                 contact_email: str, internal_id: int | None = None,
                 parent_project: dlib.ABCProject | None = None,
                 instrument: dlib.ABCInstrument | None = None,
                 created_on: datetime | None = None,
                 owner_group: dlib.ABCResearchGroup | None = None,
                 metatexts: Dict[str, dlib.ABCMetatext] = None,
                 urls: List[dlib.ABCUrl] = None):
        self._internal_id: int | None = internal_id
        self._external_id: str | None = external_id

        self._parent_project: dlib.ABCProject = parent_project
        self._instrument: dlib.ABCInstrument | None = instrument
        self._metatexts: Dict[str, dlib.ABCMetatext] | None = metatexts
        self._urls: List[dlib.ABCUrl] | None = urls

        self._contact_email: str = contact_email
        self._created_on: datetime = datetime.now(tz = None) if created_on is None else created_on
        self._owner_group: dlib.ABCResearchGroup | None = owner_group
        self._owner_user: dlib.ABCUser = owner_user
        self._state: DatasetState = state
        self._title: str = title

    @classmethod
    def _get_class_rulings(cls) -> Dict[str, Self]:
        import lib.data.sql.postgresql as sqllib
        return {"postgresql": sqllib.PostgreSQLDataset}

    @staticmethod
    @abstractmethod
    def does_exist_with_id(internal_id: int) -> bool:
        pass

    @staticmethod
    @abstractmethod
    def does_exist_with_label(label: str) -> bool:
        pass

    @staticmethod
    @abstractmethod
    def does_exist_with_labels(labels: List[str]) -> Dict[str, bool]:
        pass

    @staticmethod
    @abstractmethod
    def get_full_dataset_list() -> Dict[str, int]:
        pass

    def get_internal_id(self) -> int | None:
        return self._internal_id

    def get_external_id(self) -> int | None:
        return self._external_id

    def get_parent_project(self) -> dlib.ABCProject:
        return self._parent_project

    def get_email(self) -> str:
        return self._contact_email

    def get_created_on_date(self) -> datetime | None:
        return self._created_on

    def get_group(self) -> dlib.ABCResearchGroup | None:
        return self._owner_group

    def get_owner(self) -> dlib.ABCUser:
        return self._owner_user

    def get_instrument(self) -> dlib.ABCInstrument | None:
        return self._instrument

    def get_state(self) -> DatasetState:
        return self._state

    def get_title(self) -> str:
        return self._title

    def get_metatexts(self) -> Dict[dlib.ABCMetatext] | None:
        return self._metatexts

    def get_urls(self) -> List[dlib.ABCUrl] | None:
        return self._urls

    def has_parent(self) -> bool:
        return self._parent_project is not None

    @classmethod
    @abstractmethod
    def objectify_with_id(cls, db_id: int) -> dlib.ABCDataset:
        pass

    @classmethod
    @abstractmethod
    def objectify_with_label(cls, label: str) -> dlib.ABCDataset:
        pass

    @classmethod
    @abstractmethod
    def objectify_with_dataset(cls, dataset: dlib.ABCDataset) -> dlib.ABCDataset:
        pass

    def set(self, parent_project: dlib.ABCProject | None, instrument: dlib.ABCInstrument | None, title: str,
            owner_user: dlib.ABCUser | None, owner_group: dlib.ABCResearchGroup | None, contact_email: str,):

        self._parent_project: dlib.ABCProject = parent_project
        self._instrument: dlib.ABCInstrument | None = instrument

        self._contact_email = contact_email
        self._owner_group = owner_group
        self._owner_user = owner_user
        self._title = title

    def set_email(self, email: str):
        self._contact_email = email

    def set_group(self, group: dlib.ABCResearchGroup | None):
        self._owner_group = group

    def set_owner(self, owner: dlib.ABCUser | None):
        self._owner_user = owner

    def set_instrument(self, instrument: dlib.ABCInstrument | None):
        self._instrument = instrument

    def set_title(self, title: str):
        self._title = title

    def set_metatext(self, metatext: dlib.ABCMetatext):
        if self._metatexts is None:
            self._metatexts = {}

        self._metatexts[metatext.get_tag()] = metatext

    def set_metatexts(self, metatexts: Dict[str, dlib.ABCMetatext] | None):
        self._metatexts = metatexts

    def set_urls(self, urls: List[dlib.ABCUrl] | None):
        self._urls = urls

    def set_parent_project(self, parent: dlib.ABCProject):
        self._parent_project = parent

    @abstractmethod
    def update_state(self, state: DatasetState | None, allow_downgrade: bool = False):
        pass

    @abstractmethod
    def write_to_db(self):
        pass

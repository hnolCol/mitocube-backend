from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Self

import lib.data as dlib

class ABCResearchGroupError(dlib.ABCDataError):
    pass

class ABCResearchGroup(ABC, dlib.FlexDataClass):

    def __init__(self, name: str, name_short: str , institute: str, base64_image: str | None, profile_text: str | None,
                 contact_address: str | None, contact_email: str | None, url: str | None, db_id: int | None = None):
        self._id: int = db_id
        self._name: str = name
        self._name_short: str = name_short
        self._institute: str = institute
        self._base64_image: str | None = base64_image
        self._profile_text: str | None = profile_text
        self._contact_address: str | None = contact_address
        self._contact_email: str | None = contact_email
        self._url: str | None = url

    @classmethod
    def _get_class_rulings(cls) -> Dict[str, Self]:
        import lib.data.sql.postgresql as sqllib
        return {"postgresql": sqllib.PostgreSQLResearchGroup}

    @abstractmethod
    def does_exist(self):
        pass

    @staticmethod
    @abstractmethod
    def does_exist_with_id(db_id: int) -> bool:
        pass

    def get_id(self) -> int | None:
        return self._id

    def get_name(self) -> str:
        return self._name

    def get_short_name(self) -> str:
        return self._name_short

    def get_institute(self) -> str:
        return self._institute

    def get_base64_image(self) -> str | None:
        return self._base64_image

    def get_profile_text(self) -> str | None:
        return self._profile_text

    def get_contact_address(self) -> str | None:
        return self._contact_address

    def get_contact_email(self) -> str | None:
        return self._contact_email

    def get_url(self) -> str | None:
        return self._url

    @classmethod
    @abstractmethod
    def objectify_with_id(cls, db_id: int) -> dlib.ABCResearchGroup:
        pass

    @classmethod
    @abstractmethod
    def objectify_with_object(cls, rgroup: dlib.ABCResearchGroup) -> dlib.ABCResearchGroup:
        pass

    def set(self, db_id: int | None, name: str, name_short: str , institute: str, base64_image: str | None,
                 profile_text: str | None, contact_address: str | None, contact_email: str | None, url: str | None):
        self._id = db_id
        self._name = name
        self._name_short = name_short
        self._institute = institute
        self._base64_image = base64_image
        self._profile_text = profile_text
        self._contact_address = contact_address
        self._contact_email = contact_email
        self._url = url

    def set_id(self, db_id: int | None):
        self._id = db_id

    def set_name(self, name: str):
        self._name = name

    def set_short_name(self, name_short: str):
        self._name_short = name_short

    def set_institute(self, institute: str):
        self._institute = institute

    def set_base64_image(self, base64_image: str | None):
        self._base64_image = base64_image

    def set_profile_text(self, profile_text: str | None):
        self._profile_text = profile_text

    def set_contact_address(self, contact_address: str | None):
        self._contact_address = contact_address

    def set_contact_email(self, contact_email: str | None):
        self._contact_email = contact_email

    def set_url(self, url: str | None):
        self._url = url

    @abstractmethod
    def write_to_db(self):
        pass

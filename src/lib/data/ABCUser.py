from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from typing import Dict, List, Type, Self

import lib.data as dlib

from config import get_system_settings

class ABCUserError(dlib.ABCDataError):
    pass

class ABCUserNotFoundError(ABCUserError):
    pass

class ABCUser(ABC, dlib.FlexDataClass):
    def __init__(self, username: str, firstname: str, lastname: str, email: str,
                 research_group: dlib.ABCResearchGroup | None = None, base64_image: str | None = None,
                 profile_text: str | None = None, orcid: str | None = None,  db_id: int | None = None,
                 url: str | None = None, allow_login: bool = False, expires_after: datetime = datetime.now()):

        self._id: int | None = db_id
        self._username: str = username
        self._research_group: dlib.ABCResearchGroup | None = research_group
        self._firstname: str = firstname
        self._lastname: str = lastname
        self._email: str = email
        self._is_email_verified: bool = False  # Todo: Implement matching methods for _is_email_verified
        self._base64_image: str | None = base64_image
        self._profile_text: str | None = profile_text
        self._orcid: str | None = orcid
        self._url: str | None = url
        self._db_allow_login: bool = allow_login
        self._personal_salt: str = "lksö3g0X98+w!506wÄz3Z?f4w9vVt6_5JY0a8vc4tjwt6züSa0ctu"  # Todo: Implement get_random_string(128)
        self._created_on: datetime = datetime.now()
        self._updated_on: datetime = self._created_on
        self._last_login_on: datetime | None = None
        self._expires_after: datetime = expires_after

    @classmethod
    def _get_class_rulings(cls) -> Dict[str, Self]:
        import lib.data.sql.postgresql as sqllib
        return {"postgresql": sqllib.PostgreSQLUser}

    def _refresh_last_login_date(self):
        self._last_login_on = datetime.now()
        self._write_last_login_date()

    @abstractmethod
    def _write_last_login_date(self):
        pass

    def _refresh_update_date(self, forceWrite: bool = False):
        self._updated_on = datetime.now()

        if forceWrite:
            self.write_to_db()

    @abstractmethod
    def _test_password(self, password: str) -> bool:
        pass

    def accept_email(self, forceWrite = False):
        self._refresh_update_date(forceWrite=False)
        self._is_email_verified = True

        if forceWrite:
            self.write_to_db()

    def allow_login(self, forceWrite = False):
        self._refresh_update_date(forceWrite = False)
        self._db_allow_login = True

        if forceWrite:
            self.write_to_db()

    @abstractmethod
    def does_exist(self) -> bool:
        pass

    @staticmethod
    @abstractmethod
    def does_exist_with_id(db_id: int) -> bool:
        pass

    @staticmethod
    @abstractmethod
    def does_exist_with_username(username: str) -> bool:
        pass

    def is_expired(self) -> bool:
        return self._expires_after <= datetime.now()

    def is_login_allowed(self) -> bool:
        return self._db_allow_login and self._expires_after > datetime.now() and self._is_email_verified

    @staticmethod
    @abstractmethod
    def is_username_taken(username: str) -> bool:
        pass

    def forbid_login(self, forceWrite = False):
        self._refresh_update_date(forceWrite = False)
        self._db_allow_login = False
        # self._expires_after = datetime.now()  # Question: set _expires_after to now on top of it or keep original value?

        if forceWrite:
            self.write_to_db()

    def forbid_email(self, forceWrite = False):
        self._refresh_update_date(forceWrite=False)
        self._is_email_verified = False

        if forceWrite:
            self.write_to_db()

    @staticmethod
    @abstractmethod
    def get_users(usernames: List[str] = None) -> Dict[str, ABCUser]:
        pass

    @staticmethod
    @abstractmethod
    def get_user_names() -> Dict[str, int]:
        pass

    def get_id(self) -> int | None:
        return self._id

    def get_username(self) -> str:
        return self._username

    def get_research_group(self) -> dlib.ABCResearchGroup | None:
        return self._research_group

    def get_firstname(self) -> str:
        return self._firstname

    def get_lastname(self) -> str:
        return self._lastname

    def get_email(self) -> str:
        return self._email

    def get_base64_image(self) -> str | None:
        return self._base64_image

    def get_profile_text(self) -> str | None:
        return self._profile_text

    def get_orcid(self) -> str | None:
        return self._orcid

    def get_url(self) -> str | None:
        return self._url

    def get_allow_login_value(self) -> bool:
        return self._db_allow_login

    def get_created_on(self) -> datetime:
        return self._created_on

    def get_updated_on(self) -> datetime:
        return self._updated_on

    def get_last_login_on(self) -> datetime | None:
        return self._last_login_on

    def get_expires_after(self) -> datetime:
        return self._expires_after

    def get_refresh_updated_on(self):
        return self._updated_on

    def login(self, password: str):
        # ToDo: Test if User with specified Username exist

        if not self.is_login_allowed():
            raise ABCUserError("Login is deactivated for this user. Contact the administrator to enable login.")

        if not self._test_password(password = password):
            raise ABCUserError("Invalid credentials. Please check if the username and password were spelled correctly and try again.")

        self._refresh_last_login_date()

    @classmethod
    @abstractmethod
    def objectify_with_id(cls, db_id: int) -> ABCUser:
        pass

    @classmethod
    @abstractmethod
    def objectify_with_username(cls, username: str) -> ABCUser | None:
        pass

    @classmethod
    @abstractmethod
    def objectify_with_email(cls, email: str) -> ABCUser:
        pass

    @classmethod
    @abstractmethod
    def objectify_with_object(cls, user: ABCUser) -> ABCUser:
        pass

    def set(self, db_id: int | None, username: str, research_group: dlib.ABCResearchGroup | None, firstname: str,
            lastname: str, email: str, base64_image: str | None, profile_text: str | None, orcid: str | None,
            url: str | None, allow_login: bool, expires_after: datetime):
        self._refresh_update_date(forceWrite = False)

        self._id = db_id
        self._username = username
        self._research_group = research_group
        self._firstname = firstname
        self._lastname = lastname
        self._email = email
        self._base64_image = base64_image
        self._profile_text = profile_text
        self._orcid = orcid
        self._url = url
        self._db_allow_login = allow_login
        self._expires_after = expires_after

    def set_full(self, db_id: int | None, username: str, research_group: dlib.ABCResearchGroup | None, firstname: str,
                 lastname: str, email: str, base64_image: str | None, profile_text: str | None, orcid: str | None,
                 url: str | None, allow_login: bool, expires_after: datetime):
        self._refresh_update_date(forceWrite = False)

        self._id = db_id
        self._username = username
        self._research_group = research_group
        self._firstname = firstname
        self._lastname = lastname
        self._email = email
        self._base64_image = base64_image
        self._profile_text = profile_text
        self._orcid = orcid
        self._url = url
        self._db_allow_login = allow_login
        self._expires_after = expires_after

    def set_research_group(self, research_group: dlib.ABCResearchGroup | None):
        self._refresh_update_date(forceWrite = False)
        self._research_group = research_group

    def set_name(self, firstname: str, lastname: str):
        self._refresh_update_date(forceWrite = False)
        self._firstname = firstname
        self._lastname = lastname

    def set_firstname(self, firstname: str):
        self._refresh_update_date(forceWrite = False)
        self._firstname = firstname

    def set_lastname(self, lastname: str):
        self._refresh_update_date(forceWrite = False)
        self._lastname = lastname

    def set_email(self, email: str):
        self._refresh_update_date(forceWrite = False)
        self._email = email

    def set_base64_image(self, base64_image: str | None):
        self._refresh_update_date(forceWrite = False)
        self._base64_image = base64_image

    def set_profile_text(self, profile_text: str | None):
        self._refresh_update_date(forceWrite = False)
        self._profile_text = profile_text

    def set_orcid(self, orcid: str | None):
        self._refresh_update_date(forceWrite = False)
        self._orcid = orcid

    def set_url(self, url: str | None):
        self._refresh_update_date(forceWrite = False)
        self._url = url

    def set_allow_login(self, allow_login: bool):
        self._refresh_update_date(forceWrite = False)
        self._db_allow_login = allow_login

    def set_expires_after(self, expires_after: datetime):
        self._refresh_update_date(forceWrite = False)
        self._expires_after = expires_after

    @abstractmethod
    def write_to_db(self):
        pass

    @abstractmethod
    def write_password(self, password: str):
        pass


from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Tuple, Self
from datetime import datetime, timedelta
import string
import random
import hashlib

import lib.data as dlib

from enum import StrEnum

class ABCTokenType(StrEnum):
    EMAIL = "email"
    LOGIN = "login"
    USER = "user"
    REGISTRATION = "registration"


class ABCTokenError(Exception):
    pass

class TokenNotFoundError(ABCTokenError):
    pass
class ExpiredTokenError(ABCTokenError):
    pass

class EmailTokenError(ABCTokenError):
    pass

class UserTokenError(ABCTokenError):
    pass

class LoginTokenError(ABCTokenError):
    pass

class RegistrationTokenError(ABCTokenError):
    pass


class ABCToken(ABC, dlib.FlexDataClass):
    def __init__(self,
                 username: str | None,
                 ip: str | None,
                 agent: str | None,
                 token_type: ABCTokenType,
                 token: str | None = None,
                 md5_token: str | None = None,
                 expires_after: datetime | None = None,
                 value: str | None = None):

        if bool(token) == bool(md5_token):
            raise dlib.ABCTokenError("On have to provide provide neither or either token or md5_token")
        elif token:
            md5_token = ABCToken.token_to_md5(token)

        self._is_information_sufficient(token_type = token_type,
                                        username = username, ip = ip, agent = agent, value = value)

        self._md5_token = md5_token
        self._username: str | None = username
        self._ip: str | None = ip
        self._agent: str | None = agent
        self._token_type: ABCTokenType = token_type

        self._created_on: datetime = datetime.now()

        if expires_after:
            self._expires_after: datetime = expires_after
        else:
            self._expires_after: datetime = datetime.now()

            match token_type:
                case ABCTokenType.USER:
                    self._expires_after = self._expires_after + timedelta(hours=12)
                case ABCTokenType.EMAIL:
                    self._expires_after = self._expires_after + timedelta(hours=12)
                case ABCTokenType.LOGIN:
                    self._expires_after = self._expires_after + timedelta(minutes=10)
                case ABCTokenType.REGISTRATION:
                    self._expires_after = self._expires_after + timedelta(days=91)

        self._value: str | None = value

    @staticmethod
    @abstractmethod
    def _add_token(token: ABCToken):
        pass

    @staticmethod
    def _is_information_sufficient(token_type: ABCTokenType,
                                   username: str | None = None,
                                   ip: str | None = None,
                                   agent: str | None = None,
                                   value: str | None = None):
        match token_type:
            case ABCTokenType.USER:
                if None in [username, ip, agent]:
                    raise UserTokenError("A user token requires the username, the ip and agent information.")
            case ABCTokenType.EMAIL:
                if None in [username, ip, agent]:
                    raise EmailTokenError("A Email token requires the username, the ip and agent information.")
            case ABCTokenType.LOGIN:
                if None in [username, ip, agent]:
                    raise LoginTokenError("A Login token requires the username, the ip and agent information.")
            case ABCTokenType.REGISTRATION:
                if None in [username, ip, agent, value]:
                    raise RegistrationTokenError("A Login token requires the username, the ip, agent and a value information.")
            case _:
                raise ABCTokenError("Unknown Token Type. Unable to verify if arguments are sufficient to create a token.")

    @classmethod
    def _get_class_rulings(cls) -> Dict[str, Self]:
        import lib.data.sql.postgresql as sqllib
        return {"postgresql": sqllib.PostgreSQLToken}

    @staticmethod
    def _get_random_token_str(range_value: int, char_lib: str) -> str:
        return ''.join(random.SystemRandom().choice(char_lib) for _ in range(range_value))

    def test_token(self, token_type: ABCTokenType, agent: str | None = None, ip: str | None = None, value: str | None = None):
        if self.is_expired():
            raise ExpiredTokenError("The token is expired.")
        elif self._token_type != token_type:
            raise ABCTokenError("Provided token type does not match the saved token type.")

        match self._token_type:
            case ABCTokenType.USER:
                if self._ip is None or self._ip != ip:
                    raise UserTokenError("The token does not belong to the ip address.")
                elif self._agent is None or self._agent != agent:
                    raise UserTokenError("The token is from an unknown agent.")
            case ABCTokenType.EMAIL:
                pass  # Just requires to be not expired and to match the type and md5
            case ABCTokenType.LOGIN:
                if self._ip is None or self._ip != ip:
                    raise LoginTokenError("The token does not belong to the ip address.")
                elif self._agent is None or self._agent != agent:
                    raise LoginTokenError("The token is from an unknown agent.")
            case ABCTokenType.REGISTRATION:
                pass  # Just requires to be not expired and to match the type and md5
            case _:
                raise ABCTokenError("Unknown Token Type. Unable to verify if the token is valid.")

    @classmethod
    def create(cls, token_type: ABCTokenType,
               username: str | None = None,
               ip: str | None = None,
               agent: str | None = None,
               value: str | None = None) -> Tuple[str, Self]:
        str_token = cls.generate_new_token_str(token_type = token_type)
        token = cls(token = str_token, token_type = token_type,
                    username = username, ip = ip, agent = agent, value = value)

        # Fixme: There is a small risk that the random token is already in the database, hence maybe do it in a loop with x attempts and test before sending
        cls._add_token(token = token)
        return str_token, token

    @staticmethod
    @abstractmethod
    def clear_expired_tokens():
        pass

    @classmethod
    @abstractmethod
    def objectify_token(cls, token: str, token_type: dlib.ABCTokenType) -> ABCToken:
        pass

    @classmethod
    @abstractmethod
    def remove_token(cls, token: dlib.ABCToken):
        pass

    @staticmethod
    def generate_new_token_str(token_type: ABCTokenType) -> str:
        match token_type:
            case ABCTokenType.USER:
                return ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.ascii_lowercase + string.digits + "!#$%&*+-<=>?@~") for _ in range(128))
            case ABCTokenType.EMAIL:
                return ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(8))
            case ABCTokenType.LOGIN:
                return ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(12))
            case ABCTokenType.REGISTRATION:
                return ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.ascii_lowercase + string.digits + "!#$%&*+-<=>?@~") for _ in range(32))
            case _:
                raise ABCTokenError("Unknown Token Type. Unable to generate random token string")

    def get_agent(self) -> str | None:
        return self._agent

    def get_username(self) -> str | None:
        return self._username

    def get_ip(self) -> str | None:
        return self._ip

    def get_md5_token(self) -> str:
        return self._md5_token

    def get_token_type(self) -> ABCTokenType:
        return self._token_type

    def get_value(self) -> str | None:
        return self._value

    def get_created_on(self) -> datetime:
        return self._created_on

    def get_expires_after(self) -> datetime:
        return self._expires_after

    def is_expired(self) -> bool:
        return datetime.now() > self._expires_after

    @staticmethod
    def token_to_md5(token: str) -> str:
        return hashlib.md5(token.encode("utf-8")).hexdigest()

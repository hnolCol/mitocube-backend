from __future__ import annotations

from abc import abstractmethod
import os
from typing import Dict, Tuple, Type, Self
from datetime import datetime, timedelta
import string
# import asyncio
import random
import hashlib
import json

from lib.designpatterns import SingletonABCMeta


class MemTokenError(Exception):
    pass

class MemToken:  # ToDo: Create ABCLoginToken class
    def __init__(self, username: str, ip: str, agent: str,
                 token: str | None = None,
                 md5_token: str | None = None,
                 expires_after: timedelta = timedelta(hours=12)):

        if bool(token) == bool(md5_token):
            raise MemTokenError("On have to provide provide either token or md5_token, but not both simultaneously nor neither.")
        elif token:
            md5_token = MemToken.token_to_md5_token(token)

        self._md5_token = md5_token
        self._username = username
        self._ip = ip
        self._agent = agent

        self._created_on = datetime.now()
        self._expires_after = datetime.now() + timedelta(hours=12)  # ToDo: Create configuration

    @classmethod
    def create(cls, username: str, ip: str, agent: str) -> Tuple[str, Self]:
        str_token = cls.generate_new_token_str()
        token = cls(token = str_token, username = username, ip = ip, agent = agent)
        return str_token, token

    @staticmethod
    def generate_new_token_str(range_value: int = 128,
                               char_lib: str = string.ascii_uppercase + string.ascii_lowercase + string.digits + "!#$%&*+-<=>?@~") -> str:
        return ''.join(random.SystemRandom().choice(char_lib) for _ in range(range_value))

    def get_agent(self) -> str:
        return self._agent

    def get_username(self) -> str:
        return self._username

    def get_ip(self) -> str:
        return self._ip

    def get_md5_token(self) -> str:
        return self._md5_token

    def get_created_on(self) -> datetime:
        return self._created_on

    def get_expires_after(self) -> datetime:
        return self._expires_after

    def is_expired(self) -> bool:
        return datetime.now() > self._expires_after

    @abstractmethod
    def test(self, md5_token: str, agent: str, ip: str) -> bool:
        pass

    @staticmethod
    def token_to_md5_token(token: str) -> str:
        return hashlib.md5(token.encode("utf-8")).hexdigest()


class MemTokens(metaclass = SingletonABCMeta):
    def __init__(self, token_persist_restart: bool = False, file_persistent_memory: str | None = None):
        self._token_persist_restart: bool = token_persist_restart
        self._file_persistent_memory: str | None = file_persistent_memory

        if self._token_persist_restart and self._file_persistent_memory is None:
            raise MemTokenError("Unable to read or write tokens if argument 'path_persistent_memory' is not set correctly.")

        self._memory: Dict[str, MemToken] = {}

        self._read()

    def _read(self):
        if self._token_persist_restart:
            str_file = os.path.join(self._file_persistent_memory)

            if os.path.isfile(str_file):
                with open(str_file, "r") as in_file:
                    json_obj = json.load(in_file)

                for obj in json_obj.items():
                    token = MemToken(md5_token = obj[0],
                                     username=obj[1]["username"],
                                     ip=obj[1]["ip"],
                                     agent=obj[1]["agent"])
                    token._created_on = datetime.strptime(obj[1]["created_on"], "%Y-%m-%d, %H:%M:%S")
                    token._expires_after = datetime.strptime(obj[1]["expires_after"], "%Y-%m-%d, %H:%M:%S")
                    self._memory[obj[0]] = token

                os.remove(str_file)

    def _write(self):
        if self._token_persist_restart:
            json_obj: Dict[str, Dict[str, str]] = {}

            self.clear_expired_tokens()

            for key, obj in self._memory.items():
                json_obj[key] = {"username": obj.get_username(),
                                 "ip": obj.get_ip(),
                                 "agent": obj.get_agent(),
                                 "created_on": obj.get_created_on().strftime("%Y-%m-%d, %H:%M:%S"),
                                 "expires_after": obj.get_expires_after().strftime("%Y-%m-%d, %H:%M:%S")}

            with open(self._file_persistent_memory, "w+") as out_file:
                json.dump(json_obj, out_file)

    def close(self):
        self._write()

    def get_stored_session_tokens(self) -> Dict[str, MemToken]:
        return self._memory

    def remove_token(self, token: MemToken):
        try:
            self._memory.pop(token.get_md5_token())
        except KeyError:
            pass

    def test_token(self, token: str, ip: str, agent: str) -> MemToken:
        try:
            md5_token = MemToken.token_to_md5_token(token)
            obj = self._memory[md5_token]

            try:
                obj.test(md5_token = md5_token, agent = agent, ip = ip)
            except MemToken as err:
                if obj.is_expired():
                    self._memory.pop(token)
                raise err
        except KeyError:
            raise MemTokenError("Token does not exist.")

        return obj

    # ToDo: make it thread safe https://docs.python.org/3/library/asyncio-task.html
    # Fixme: async with MemLoginTokens.__lock: async <coroutine object MemLoginTokens.create_token at 0x7ff46a5f9ad0>
    def create_token(self, username: str, ip: str, agent: str, n_attempts: int = 42) -> str:
        str_token: str
        token: MemToken
        it: int = 0

        if random.random() > 0.95:  # Check for expired tokens every 20th-ish attempt
            self.clear_expired_tokens()

        while True:
            str_token, token = self.get_token_class().create(username = username, ip = ip, agent = agent)
            md5_token = token.get_md5_token()
            it += 1

            if md5_token not in self._memory.keys():
                self._memory[md5_token] = token
                break
            elif it > n_attempts:
                raise MemTokenError("Unable to create unique token!")

        return str_token

    def clear(self):
        # async with MemLoginTokens.__lock:
        self._memory = {}

    def clear_expired_tokens(self):
        # async with MemLoginTokens.__lock:
        for token, obj in self._memory.items():
            if obj.is_expired():
                self._memory.pop(token)

    @staticmethod
    def get_token_class() -> Type[MemToken]:
        return MemToken

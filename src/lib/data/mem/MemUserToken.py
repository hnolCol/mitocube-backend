from __future__ import annotations

import os
from typing import Dict
from datetime import datetime, timedelta
import string
import asyncio
import random
import hashlib
import json

from lib.designpatterns import SingletonABCMeta


class MemUserTokenError(Exception):
    pass

class MemUserTokens(metaclass = SingletonABCMeta):
    def __init__(self, token_persist_restart: bool = False, path_persistent_memory: str | None = None):
        self._token_persist_restart: bool = token_persist_restart
        self._path_persistent_memory: str | None = path_persistent_memory

        if self._token_persist_restart and self._path_persistent_memory is None:
            raise MemUserTokenError("Unable to read or write tokens if argument 'path_persistent_memory' is not set correctly.")

        self._memory: Dict[str, MemUserToken] = {}

        self._read()

    def _read(self):
        if self._token_persist_restart:
            str_file = os.path.join(self._path_persistent_memory, ".cube_tokens.json")

            if os.path.isfile(str_file):
                with open(str_file, "r") as in_file:
                    json_obj = json.load(in_file)

                for obj in json_obj.items():
                    token = MemUserToken(md5_token = obj[0],
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

            with open(os.path.join(self._path_persistent_memory, ".cube_tokens.json"), "w+") as out_file:
                json.dump(json_obj, out_file)

    def close(self):
        self._write()

    def get_stored_session_tokens(self) -> Dict[str, MemUserToken]:
        return self._memory

    def test_token(self, token: str, ip: str, agent: str) -> MemUserToken:
        try:
            md5_token = MemUserToken.token_to_md5_token(token)
            obj = self._memory[md5_token]

            try:
                obj.test(md5_token = md5_token, agent = agent, ip = ip)
            except MemUserTokenError as err:
                if obj.is_expired():
                    self._memory.pop(token)
                raise err
        except KeyError:
            raise MemUserTokenError("Token does not exist.")

        return obj

    # ToDo: make it thread safe https://docs.python.org/3/library/asyncio-task.html
    # Fixme: async with MemLoginTokens.__lock: async <coroutine object MemLoginTokens.create_token at 0x7ff46a5f9ad0>
    def create_token(self, username: str, ip: str, agent: str, n_attempts: int = 42) -> str:
        token: str
        it: int = 0

        if random.random() > 0.95:  # Check for expired tokens every 20th-ish attempt
            self.clear_expired_tokens()

        while True:
            token = MemUserToken.create_new_token()
            md5_token = MemUserToken.token_to_md5_token(token)
            it += 1

            if md5_token not in self._memory.keys():
                self._memory[md5_token] = MemUserToken(md5_token = md5_token, username = username, ip = ip, agent = agent)
                break
            elif it > n_attempts:
                raise MemUserTokenError("Unable to create unique token!")

        return token

    def clear(self):
        # async with MemLoginTokens.__lock:
        self._memory = {}

    def clear_expired_tokens(self):
        # async with MemLoginTokens.__lock:
        for token, obj in self._memory.items():
            if obj.is_expired():
                self._memory.pop(token)


class MemUserToken:  # ToDo: Create ABCLoginToken class
    def __init__(self, username: str, ip: str, agent: str,
                 token: str | None = None,
                 md5_token: str | None = None):

        if bool(token) != bool(md5_token):
            raise MemUserTokenError("On have to provide provide either token or md5_token, but not both simultaneously nor neither.")
        elif token:
            md5_token = MemUserToken.token_to_md5_token(token)

        self._md5_token = md5_token
        self._username = username
        self._ip = ip
        self._agent = agent

        self._created_on = datetime.now()
        self._expires_after = datetime.now() + timedelta(hours=12)  # ToDo: Create configuration

    @staticmethod
    def create_new_token(range_value: int = 128,
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

    def test(self, md5_token: str, agent: str, ip: str) -> bool:
        if self._md5_token != md5_token:
            raise MemUserTokenError("Provided md5 token does not match the saved md5 token.")
        if self.is_expired():
            raise MemUserTokenError("The token is expired.")
        elif self._ip != ip:
            raise MemUserTokenError("The token does not belong to the ip address.")
        elif self._agent != agent:
            raise MemUserTokenError("The token is from an unknown agent.")

        return True

    @staticmethod
    def token_to_md5_token(token: str) -> str:
        return hashlib.md5(token.encode("utf-8")).hexdigest()

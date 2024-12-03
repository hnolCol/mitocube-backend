from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import random
import string
from typing import Dict, Tuple
import hashlib

from lib.designpatterns import SingletonABCMeta


class MemLoginTokenError(Exception):
    pass


class MemLoginToken:  # ToDo: Create ABCLoginToken class
    def __init__(self, username: str, ip: str, agent: str,
                 token: str | None = None,
                 md5_token: str | None = None):

        if bool(token) == bool(md5_token):
            raise MemLoginTokenError("On have to provide provide either token or md5_token, but not both simultaneously nor neither.")
        elif token:
            md5_token = MemLoginToken.token_to_md5_token(token)

        self._md5_token = md5_token
        self._username = username
        self._ip = ip
        self._agent = agent

        self._created_on = datetime.now()
        self._expires_after = datetime.now() + timedelta(minutes=6)  # ToDo: Create configuration

    @staticmethod
    def create(username: str, ip: str, agent: str) -> Tuple[str, MemLoginToken]:
        str_token = MemLoginToken.generate_new_token()
        token = MemLoginToken(token = str_token, username = username, ip = ip, agent = agent)
        return str_token, token

    @staticmethod
    def generate_new_token(range_value: int = 12,
                           char_lib: str = string.ascii_uppercase + string.ascii_lowercase + string.digits) -> str:
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
            raise MemLoginTokenError("Provided md5 token does not match the saved md5 token.")
        if self.is_expired():
            raise MemLoginTokenError("The token is expired.")
        elif self._ip != ip:
            raise MemLoginTokenError("The token does not belong to the ip address.")
        elif self._agent != agent:
            raise MemLoginTokenError("The token is from an unknown agent.")

        return True

    @staticmethod
    def token_to_md5_token(token: str) -> str:
        return hashlib.md5(token.encode("utf-8")).hexdigest()


class MemLoginTokens(metaclass=SingletonABCMeta):
    def __init__(self):
        self._memory: Dict[str, MemLoginToken] = {}
        # self.__lock = asyncio.Lock()

    def test_token(self, token: str, ip: str, agent: str) -> MemLoginToken:
        try:
            md5_token = MemLoginToken.token_to_md5_token(token)
            obj = self._memory[md5_token]

            try:
                obj.test(md5_token = md5_token, agent = agent, ip = ip)
            except MemLoginTokenError as err:
                if obj.is_expired():
                    self._memory.pop(token)
                raise err
        except KeyError:
            raise MemLoginTokenError("Token does not exist.")

        return obj

    # ToDo: make it thread safe https://docs.python.org/3/library/asyncio-task.html
    # Fixme: async <coroutine object MemLoginTokens.create_token at 0x7ff46a5f9ad0>
    def create_token(self, username: str, ip: str, agent: str, n_attempts: int = 42) -> str:
        str_token: str
        token: MemLoginToken
        it: int = 0

        if random.random() > 0.95:  # Check for expired tokens every 20th-ish attempt
            self.clear_expired_tokens()

        # async with MemLoginTokens.__lock:
        while True:
            str_token, token = MemLoginToken.create(username = username, ip = ip, agent = agent)
            md5_token = token.get_md5_token()
            it += 1

            if md5_token not in self._memory.keys():
                self._memory[md5_token] = token
                break
            elif it > n_attempts:
                raise MemLoginTokenError("Unable to create unique token!")

        return str_token

    def clear(self):
        # async with MemLoginTokens.__lock:
        self._memory = {}

    def clear_expired_tokens(self):
        # async with MemLoginTokens.__lock:
        for token, obj in self._memory.items():
            if obj.is_expired():
                self._memory.pop(token)

    def remove_token(self, token: MemLoginToken):
        try:
            self._memory.pop(token.get_md5_token())
        except KeyError:
            pass

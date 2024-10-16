from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import random
import string
from typing import Dict
import os.path
import json

from lib.designpatterns import SingletonABCMeta


class ABCUserTokenError(Exception):
    pass

class MemUserTokens(metaclass=SingletonABCMeta):  # ToDo: Create ABCLoginTokens class
    def __init__(self):
        self._memory: Dict[str, MemUserToken] = {}  # Question: Trying it this way instead of singleton, is it okay to do?
        # self.__lock = asyncio.Lock()

        self._read()

    # def __del__(self):  # Question, does not work. Any other options? will be removed but curious: ImportError: sys.meta_path is None, Python is likely shutting down
    #     self._write()

    def _read(self):
        print("> _read(self):")
        if os.path.isfile("/home/andreaslindner/mitocube_tokens.json"):
            with open("/home/andreaslindner/mitocube_tokens.json", "r") as in_file:
                json_obj = json.load(in_file)

            for obj in json_obj.items():
                token = MemUserToken(token = obj[0],
                                     username=obj[1]["username"],
                                     ip=obj[1]["ip"],
                                     agent=obj[1]["agent"])
                token._created_on = datetime.strptime(obj[1]["created_on"], "%Y-%m-%d, %H:%M:%S")
                token._expires_after = datetime.strptime(obj[1]["expires_after"], "%Y-%m-%d, %H:%M:%S")
                self._memory[obj[0]] = token

    def _write(self):  # Fixme: Write it to SQL Database
        json_obj: Dict[str, Dict[str, str]] = {}

        for key, obj in self._memory.items():
            json_obj[key] = {"username": obj.get_username(),
                             "ip": obj.get_ip(),
                             "agent": obj.get_agent(),
                             "created_on": obj.get_created_on().strftime("%Y-%m-%d, %H:%M:%S"),
                             "expires_after": obj.get_expires_after().strftime("%Y-%m-%d, %H:%M:%S")}

        with open("/home/andreaslindner/mitocube_tokens.json", "w+") as out_file:
            json.dump(json_obj, out_file)

    def test_token(self, token: str, ip: str, agent: str) -> MemUserToken:
        try:
            obj = self._memory[token]  # Question: test better rather than await exception?

            if obj.is_expired():
                self._memory.pop(token)  # Might also throw an KeyError if it was removed in the meanwhile
                raise ABCUserTokenError("The token '{}' is expired.".format(token))
            elif obj.get_ip() != ip:
                raise ABCUserTokenError("The token '{}' does not belong to the ip '{}'.".format(token, ip))
            elif obj.get_agent() != agent:
                raise ABCUserTokenError("The token '{}' is from an unknown agent.".format(token))

            return obj

        except KeyError:  # as err:
            raise ABCUserTokenError("Token '{}' does not exist.".format(token))

    # Fixme: async <coroutine object MemLoginTokens.create_token at 0x7ff46a5f9ad0>
    def create_token(self, username: str, ip: str, agent: str) -> str:  # ToDo: make it thread safe https://docs.python.org/3/library/asyncio-task.html
        token: str
        it: int = 0

        # Fixme: SyntaxError: 'async with' outside async function
        # async with MemLoginTokens.__lock:
        while True:
            token = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.ascii_lowercase + string.digits + "!#$%&*+-<=>?@~") for _ in
                            range(128))  # ToDo: Create a own token class, not secure yet
            it += 1

            if token not in self._memory.keys():
                self._memory[token] = MemUserToken(token=token, username=username, ip=ip, agent=agent)
                break
            elif it > 42:
                raise Exception("Unable to create unique token!")

        return token

    # Fixme: async <coroutine object MemLoginTokens.create_token at 0x7ff46a5f9ad0>
    def clear(self):
        # Fixme: SyntaxError: 'async with' outside async function
        # async with MemLoginTokens.__lock:
        self._memory = {}

    # Fixme: async <coroutine object MemLoginTokens.create_token at 0x7ff46a5f9ad0>
    def clear_expired_tokens(self):  # Fixme: maybe run me on a cronjob or when creating a token
        # Fixme: SyntaxError: 'async with' outside async function
        # async with MemLoginTokens.__lock:
        for token, obj in self._memory.items():
            if obj.is_expired():
                self._memory.pop(token)


class MemUserToken:  # ToDo: Create ABCLoginToken class
    def __init__(self,
                 token: str,
                 username: str,
                 ip: str,
                 agent: str):
        self._token = token
        self._username = username
        self._ip = ip
        self._agent = agent

        self._created_on = datetime.now()
        self._expires_after = datetime.now() + timedelta(hours=12)  # ToDo: Create configuration

    def get_agent(self) -> str:
        return self._agent

    def get_username(self) -> str:
        return self._username

    def get_ip(self) -> str:
        return self._ip

    def get_token(self) -> str:
        return self._token

    def get_created_on(self) -> datetime:
        return self._created_on

    def get_expires_after(self) -> datetime:
        return self._expires_after

    def is_expired(self) -> bool:
        return datetime.now() > self._expires_after

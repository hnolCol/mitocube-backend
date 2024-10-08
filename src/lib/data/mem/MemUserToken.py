from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import random
import string
from typing import Any, Dict

class ABCUserTokenError(Exception):
    pass

class MemUserTokens:  # ToDo: Create ABCLoginTokens class
    __memory: Dict[str, MemUserToken] = {}  # Question: Trying it this way instead of singleton, is it okay to do?
    # __lock = asyncio.Lock()

    @staticmethod
    def test_token(token: str, ip: str, agent: str) -> MemUserToken:
        try:
            obj = MemUserTokens.__memory[token]  # Question: test better rather than await exception?

            if obj.is_expired():
                MemUserTokens.__memory.pop(token)  # Might also throw an KeyError if it was removed in the meanwhile
                raise ABCUserTokenError("The token '{}' is expired.".format(token))
            elif obj.get_ip() != ip:
                raise ABCUserTokenError("The token '{}' does not belong to the ip '{}'.".format(token, ip))
            elif obj.get_agent() != agent:
                raise ABCUserTokenError("The token '{}' is from an unknown agent.".format(token))

            return obj

        except KeyError:  # as err:
            raise ABCUserTokenError("Token '{}' does not exist.".format(token))

    # Fixme: async <coroutine object MemLoginTokens.create_token at 0x7ff46a5f9ad0>
    @staticmethod
    def create_token(username: str, ip: str, agent: str) -> str:  # ToDo: make it thread safe https://docs.python.org/3/library/asyncio-task.html
        token: str
        it: int = 0

        # Fixme: SyntaxError: 'async with' outside async function
        # async with MemLoginTokens.__lock:
        while True:
            token = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.ascii_lowercase + string.digits + "!#$%&*+-<=>?@~") for _ in
                            range(512))  # ToDo: Create a own token class, not secure yet
            it += 1

            if token not in MemUserTokens.__memory.keys():
                MemUserTokens.__memory[token] = MemUserToken(username=username, ip=ip, agent=agent)
                break
            elif it > 42:
                raise Exception("Unable to create unique token!")

        return token

    # Fixme: async <coroutine object MemLoginTokens.create_token at 0x7ff46a5f9ad0>
    @staticmethod
    def clear():
        # Fixme: SyntaxError: 'async with' outside async function
        # async with MemLoginTokens.__lock:
        MemUserTokens.__memory = {}

    # Fixme: async <coroutine object MemLoginTokens.create_token at 0x7ff46a5f9ad0>
    @staticmethod
    def clear_expired_tokens():  # Fixme: maybe run me on a cronjob or when creating a token
        # Fixme: SyntaxError: 'async with' outside async function
        # async with MemLoginTokens.__lock:
        for token, obj in MemUserTokens.__memory.items():
            if obj.is_expired():
                MemUserTokens.__memory.pop(token)


class MemUserToken:  # ToDo: Create ABCLoginToken class
    def __init__(self,
                 username: str,
                 ip: str,
                 agent: str):
        self.username = username
        self.ip = ip
        self.agent = agent

        self.created_on = datetime.now()
        self.expires_after = datetime.now() + timedelta(hours=12)  # ToDo: Create configuration

    def get_agent(self) -> str:
        return self.agent

    def get_username(self) -> str:
        return self.username

    def get_ip(self) -> str:
        return self.ip

    def is_expired(self) -> bool:
        return datetime.now() > self.expires_after

from __future__ import annotations
import random
import string

from typing import Type

from lib.data.mem import MemToken, MemTokens, MemTokenError


class MemEmailTokenError(MemTokenError):
    pass


class MemEmailToken(MemToken):
    @staticmethod
    def generate_new_token_str(range_value: int = 8,
                               char_lib: str = string.ascii_uppercase + string.ascii_lowercase + string.digits) -> str:
        return ''.join(random.SystemRandom().choice(char_lib) for _ in range(range_value))

    def test(self, md5_token: str, agent: str, ip: str) -> bool:
        if self._md5_token != md5_token:
            raise MemEmailTokenError("Provided md5 token does not match the saved md5 token.")
        if self.is_expired():
            raise MemEmailTokenError("The token is expired.")

        return True


class MemEmailTokens(MemTokens):
    def __init__(self,
                 token_persist_restart: bool = True,
                 file_persistent_memory: str | None = "/home/andreaslindner/Projects/MitoCube/.cube_tokens.registration.json"):
        super().__init__(token_persist_restart = token_persist_restart,
                         file_persistent_memory = file_persistent_memory)

    @staticmethod
    def get_token_class() -> Type[MemEmailToken]:
        return MemEmailToken

class MemLoginTokenError(MemTokenError):
    pass


class MemLoginToken(MemToken):
    @staticmethod
    def generate_new_token_str(range_value: int = 12,
                               char_lib: str = string.ascii_uppercase + string.ascii_lowercase + string.digits) -> str:
        return ''.join(random.SystemRandom().choice(char_lib) for _ in range(range_value))

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


class MemLoginTokens(MemTokens):
    def __init__(self,
                 token_persist_restart: bool = False,
                 file_persistent_memory: str | None = None):
        super().__init__(token_persist_restart = token_persist_restart,
                         file_persistent_memory = file_persistent_memory)

    @staticmethod
    def get_token_class() -> Type[MemLoginToken]:
        return MemLoginToken

class MemUserTokenError(MemTokenError):
    pass


class MemUserToken(MemToken):
    @staticmethod
    def generate_new_token_str(range_value: int = 128,
                               char_lib: str = string.ascii_uppercase + string.ascii_lowercase + string.digits + "!#$%&*+-<=>?@~") -> str:
        return ''.join(random.SystemRandom().choice(char_lib) for _ in range(range_value))

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


class MemUserTokens(MemTokens):
    def __init__(self,
                 token_persist_restart: bool = True,
                 file_persistent_memory: str | None = "/home/andreaslindner/Projects/MitoCube/.cube_tokens.json"):
        super().__init__(token_persist_restart=token_persist_restart,
                         file_persistent_memory=file_persistent_memory)

    @staticmethod
    def get_token_class() -> Type[MemUserToken]:
        return MemUserToken

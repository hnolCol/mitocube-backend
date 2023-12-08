from abc import ABC, ABCMeta, abstractmethod

from datetime import datetime, timedelta
from threading import Lock
from typing import Any, Dict, Generic, TypeVar

T = TypeVar("T")

class ExpiredValueError(Exception):
    pass

class ExpiringValue(Generic[T]):
    """
    Cache a value until it expires. Throws either an ExpiredValueError or updates value with defined function.
    """

    def __init__(self, expireTime=timedelta(seconds = 60), value:T = None, updateProcess = None):
        # datetime.timedelta(days=0, seconds=0, microseconds=0, milliseconds=0, minutes=0, hours=0, weeks=0)
        self._lock = Lock()

        self.expireTime = expireTime
        self.expiresAt = datetime.now() + self.expireTime
        self.value = value
        self.updateProcess = updateProcess

    def isExpired(self) -> bool:
        """Returns True if value is expired. Does not trigger the process to refresh the value when called. """
        return datetime.now() > self.expiresAt

    def getTimeRemaining(self):
        """Get the time left until the item will expire"""
        return self.expiresAt - datetime.now()

    def get(self) -> T:
        """Returns the saved value. Refreshes the value if it is expired using updateProcess, but raises an ExpiredValueError Exception if value is expired with no updateProcess defined. """
        if self.isExpired():
            return self.update()
        else:
            return self.value

    def update(self) -> T:
        """Update and returns the saved value using updateProcess, but raises an ExpiredValueError Exception if value is expired with no updateProcess defined. """

        if self.updateProcess is not None:
            if self._lock.locked():
                self._lock.acquire()  # update in progress, wait and return updated value
                self._lock.release()
            else:
                self._lock.acquire()  # no update in progress yet, so block, update and release
                self.value = self.updateProcess()
                self.expiresAt = datetime.now() + self.expireTime
                self._lock.release()
        else:
            raise ExpiredValueError("Value saved expired at %s with no update process defined." % self.expiresAt.strftime("%m/%d/%Y, %H:%M:%S"))

        return self.value

    def setProcessExpires(self, updateProcess = None):
        """Sets a function called to update the value if the value is requested but expired."""
        self.updateProcess = updateProcess


class JsonSerializable(ABC):
    """Provides toJson() method for JSON dictionary serialisation."""

    @abstractmethod
    def toJson(self) -> Dict[str, Any]:
        """Serialises the object into a JSON dictionary."""
        pass


class SingletonABCMeta(ABCMeta):
    """Thread-safe Singleton ABC meta-class."""

    #: Holds the singleton instance
    _instances = {}

    #: Lock used for multi-threading
    _lock: Lock = Lock()

    def __call__(cls, *args, **kwargs):
        """
        Return a list of random ingredients as strings.

        :param kind: Optional "kind" of ingredients.
        :type kind: list[str] or None
        :raise lumache.InvalidKindError: If the kind is invalid.
        :return: The ingredients list.
        :rtype: list[str]
        """
        with cls._lock:
            if cls not in cls._instances:
                instance = super().__call__(*args, **kwargs)
                cls._instances[cls] = instance
        return cls._instances[cls]


class SingletonMeta(type):
    """Thread-safe Singleton meta-class."""

    #: Holds the singleton instance
    _instances = {}

    #: Lock used for multi-threading
    _lock: Lock = Lock()

    def __call__(cls, *args, **kwargs):
        """
        Return a list of random ingredients as strings.

        :param kind: Optional "kind" of ingredients.
        :type kind: list[str] or None
        :raise lumache.InvalidKindError: If the kind is invalid.
        :return: The ingredients list.
        :rtype: list[str]
        """
        with cls._lock:
            if cls not in cls._instances:
                instance = super().__call__(*args, **kwargs)
                cls._instances[cls] = instance
        return cls._instances[cls]


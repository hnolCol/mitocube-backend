from datetime import datetime, timedelta
from threading import Lock
from typing import Any, Callable, Dict, Generic, TypeVar

T = TypeVar("T")

class ExpiredValueError(Exception):
    pass

class ExpiringValue(Generic[T]):
    """
    Cache a value until it expires. Throws either an ExpiredValueError or updates value with defined function.
    """

    def __init__(self, expireTime = timedelta(seconds = 60), value: T | None = None, updateProcess: Callable = None):
        # datetime.timedelta(days=0, seconds=0, microseconds=0, milliseconds=0, minutes=0, hours=0, weeks=0)
        self._lock = Lock()

        self._expireTime = expireTime
        self._expiresAt = datetime.now() + self._expireTime
        if value is not None:
            self._value = value
        elif updateProcess is not None:
            self._value = updateProcess()
        else:
            raise ExpiredValueError("Neither value nor update process were set!")

        self.updateProcess = updateProcess

    def isExpired(self) -> bool:
        """Returns True if value is expired. Does not trigger the process to refresh the value when called. """
        return datetime.now() > self._expiresAt

    def get_time_remaining(self):
        """Get the time left until the item will expire"""
        return self._expiresAt - datetime.now()

    def get(self) -> T:
        """Returns the saved value. Refreshes the value if it is expired using updateProcess, but raises an ExpiredValueError Exception if value is expired with no updateProcess defined. """
        if self.isExpired():
            return self.update()
        else:
            return self._value

    def update(self) -> T:
        """Update and returns the saved value using updateProcess, but raises an ExpiredValueError Exception if value is expired with no updateProcess defined. """

        if self.updateProcess is not None:
            if self._lock.locked():
                self._lock.acquire()  # update in progress, wait and return updated value
                self._lock.release()
            else:
                self._lock.acquire()  # no update in progress yet, so block, update and release
                self._value = self.updateProcess()
                self._expiresAt = datetime.now() + self._expireTime
                self._lock.release()
        else:
            raise ExpiredValueError("Value saved expired at %s with no update process defined." % self._expiresAt.strftime("%m/%d/%Y, %H:%M:%S"))

        return self._value

    def set_process_expires(self, updateProcess = None):
        """Sets a function called to update the value if the value is requested but expired."""
        self.updateProcess = updateProcess


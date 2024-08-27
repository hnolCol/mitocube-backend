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


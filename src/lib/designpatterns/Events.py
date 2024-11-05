from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from threading import Lock, Thread
from typing import List, TypeVar

T = TypeVar("T")

# Better (threadsafe) solution? https://python-3-patterns-idioms-test.readthedocs.io/en/latest/Observer.html

class Event:  # fixme: rename to something else (threading.Event !!!)
    def __init__(self, source: T, message: str):
        self._source_object: T = source
        self._message: str = message
        self._timestamp: datetime = datetime.now()

    def get_message(self) -> str:
        return self._message

    def get_timestamp(self) -> datetime:
        return self._timestamp

    def get_source(self) -> T:
        return self._source_object


class EventObservable(ABC):
    """
    The Subject interface declares a set of methods for managing subscribers.
    """

    def __init__(self):
        self._lock: Lock = Lock()
        self._observers: List[EventObserver] = []

    def attach_observer(self, observer: EventObserver):

        with self._lock:
            if observer not in self._observers:
                self._observers.append(observer)

    def detach_all_observers(self):
        with self._lock:
            self._observers.clear()

    def detach_observer(self, observer: EventObserver):
        with self._lock:
            if observer in self._observers:
                self._observers.remove(observer)

    def notify_observer(self, event: Event):
        with self._lock:
            for observer in self._observers:
                # if modifier != observer:
                observer.process_event(event=event)

    def notify_observer_with_thread(self, event: Event):  # fixme: counter check if the threading here is an good idea and solved properly!
        # todo: check https://www.geeksforgeeks.org/multithreading-python-set-1/
        # https://docs.python.org/3/library/threading.html

        with self._lock:
            observers = self._observers.copy()

        def notify_within_thread(local_event: Event, local_observers: List[EventObserver]):
            for observer in local_observers:
                observer.process_event(event=event)

        t = Thread(target = notify_within_thread, args = (event, observers))
        t.start()


class EventObserver(ABC):
    @abstractmethod
    def process_event(self, event: Event):
        pass
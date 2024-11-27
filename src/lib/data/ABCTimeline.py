from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from enum import StrEnum, unique
from typing import Dict, List, Self

import lib.data as dlib


@unique
class TimelineEventState(StrEnum):  # remember Flag https://docs.python.org/3/howto/enum.html
    NORMAL = "normal"  # ToDo: Adding missing states to TimelineEventState!
    QUERY = "query"
    LOG = "log"
    COMMAND = "command"
    REQUEST = "request"
    DATA = "data"
    REPLY = "reply"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@unique
class DatasetTimelineEventType(StrEnum):  # remember Flag https://docs.python.org/3/howto/enum.html
    NEW = "new"  # ToDo: Adding missing states to DatasetTimelineEventType!
    INITIATED = "initiated"
    UPLOADED = "uploaded"
    DATASET_ADDED = "dataset_added"
    UPDATE_ATTRIBUTES = "update_attributes"
    UPDATE_DATA = "update_data"
    UPDATE_STATE = "update_state"
    DATASET_MEASURED = "dataset_measured"
    UPDATE_META = "update_meta"
    ACTIVATED = "activated"
    RETRACTED = "retracted"
    HIDDEN = "hidden"


class ABCTimelineError(dlib.ABCDataError):
    pass


class ABCTimeline(ABC, dlib.FlexDataClass):
    def __init__(self):
        pass

    @classmethod
    def _get_class_rulings(cls) -> Dict[str, Self]:
        import lib.data.sql.postgresql as sqllib
        return {"postgresql": sqllib.PostgreSQLTimeline}

    @classmethod
    @abstractmethod
    def add_new_dataset_timeline_event(cls, user: dlib.ABCUser | None, state: dlib.TimelineEventState, text: str | None,
                                       event_type: dlib.DatasetTimelineEventType, dataset_id: int | None,
                                       timestamp: datetime = datetime.now(tz=None)) -> ABCDatasetTimelineEvent:
        pass

    @classmethod
    @abstractmethod
    def objectify_with_dataset_id(cls, dataset_id: int) -> List[dlib.ABCDatasetTimelineEvent]:
        pass

    @classmethod
    @abstractmethod
    def objectify_with_dataset_label(cls, dataset_label: str) -> List[dlib.ABCDatasetTimelineEvent]:
        pass

class ABCTimelineEvent(ABC, dlib.FlexDataClass):

    def __init__(self, db_id: int | None, timestamp: datetime, user: None | dlib.ABCUser, state: TimelineEventState, text: str | None):
        self._id: int | None = db_id
        self._timestamp: datetime = timestamp
        self._user: None | dlib.ABCUser = user
        self._state: TimelineEventState = state
        self._text: str | None = text

    @classmethod
    def _get_class_rulings(cls) -> Dict[str, Self]:
        import lib.data.sql.postgresql as sqllib
        return {"postgresql": sqllib.PostgreSQLDatasetTimelineEvent}

    def get_id(self) -> int | None:
        return self._id

    def get_timestamp(self) -> datetime:
        return self._timestamp

    def get_user(self) -> None | dlib.ABCUser:
        return self._user

    def get_state(self) -> TimelineEventState | None:
        return self._state

    def get_text(self) -> str | None:
        return self._text

    def set(self, timestamp: datetime, user: dlib.ABCUser | None, state: TimelineEventState, text: str | None):
        self._timestamp = timestamp
        self._user = user
        self._state = state
        self._text = text

    def set_id(self, db_id: int | None):
        self._id = db_id

    def set_timestamp(self, timestamp: datetime):
        self._timestamp = timestamp

    def set_user(self, user: None | dlib.ABCUser):
        self._user = user

    def set_state(self, state: TimelineEventState):
        self._state = state

    def set_text(self, text: str | None):
        self._text = text

    @abstractmethod
    def write_to_db(self):
        pass


class ABCDatasetTimelineEvent(ABCTimelineEvent):

    def __init__(self, db_id: int | None, timestamp: datetime, user: dlib.ABCUser | None, state: TimelineEventState, text: str | None,
                 event_type: DatasetTimelineEventType, dataset_id: int | None):
        super().__init__(db_id=db_id, timestamp=timestamp, user=user, state=state, text=text)
        self._event_type = event_type
        self._dataset_id = dataset_id

    def get_dataset_id(self) -> int:
        return self._dataset_id

    def get_type(self) -> DatasetTimelineEventType:
        return self._event_type

    @abstractmethod
    def write_to_db(self):
        pass

    def set(self, timestamp: datetime, user: dlib.ABCUser | None, state: TimelineEventState, text: str | None,
            event_type: DatasetTimelineEventType, dataset_id: int | None):  # Fixme: Overwriting methods with different argument signature in python.  Liskov Substitution Principle?
        super(ABCDatasetTimelineEvent, self).set(timestamp=timestamp, user=user, state=state, text=text)
        self._dataset_id = dataset_id
        self._event_type = event_type

    def set_dataset_id(self, dataset_id: int | None):
        self._dataset_id = dataset_id

    def set_type(self, event_type: DatasetTimelineEventType):
        self._event_type = event_type


from __future__ import annotations

from datetime import datetime
from typing import Dict, List

import lib.data as dlib
import lib.data.sql.postgresql as psql

class PostgreSQLTimeline(dlib.ABCTimeline):

    @classmethod
    def add_new_dataset_timeline_event(cls, user: dlib.ABCUser | None, state: dlib.TimelineEventState, text: str | None,
                                       event_type: dlib.DatasetTimelineEventType, dataset_id: int | None,
                                       timestamp: datetime = datetime.now(tz=None)) -> PostgreSQLDatasetTimelineEvent:
        event = PostgreSQLDatasetTimelineEvent(db_id=None, timestamp=timestamp, user=user, state=state, text=text, event_type=event_type, dataset_id=dataset_id)
        event.write()
        return event

    @classmethod
    def receive_for_dataset(cls, dataset_id: int) -> List[PostgreSQLDatasetTimelineEvent]:
        events: List[PostgreSQLDatasetTimelineEvent] = []
        users: Dict[int, psql.PostgreSQLUser] = {}

        try:
            db_conn = psql.PostgreSQLConnection().getConnection()
            db_cur = db_conn.cursor()

            db_cur.execute("SELECT id, event_on, created_by, type, state, comment FROM dataset_timeline_events WHERE dataset_id = %(dataset_id)s ORDER BY event_on DESC;",
                           {"dataset_id": dataset_id})

            for db_row in db_cur:  # db_cur.rowcount  # db_cur.rowcount
                if db_row[2] not in users:
                    users[db_row[2]] = psql.PostgreSQLUser.create_from_id(db_row[2])  # ToDo: Improve Create / Receive user object by id

                events.append(PostgreSQLDatasetTimelineEvent(db_id=db_row[0], timestamp=db_row[1], user=users[db_row[2]],
                                                             state=db_row[4], text=db_row[5], event_type=db_row[3], dataset_id=dataset_id))

            psql.PostgreSQLConnection().returnConnection(db_conn)
        except Exception as err:
            if "db_cur" in locals():
                psql.PostgreSQLConnection().returnConnection(db_conn)
            raise err
        return events


class PostgreSQLDatasetTimelineEvent(dlib.ABCDatasetTimelineEvent):
    def __db_insert(self):
        if self._id:
            raise dlib.ABCTimelineError("Unable to perform database INSERT with PostgreSQLDatasetTimelineEvent that does already exist in database.")

        try:
            db_conn = psql.PostgreSQLConnection().getConnection()
            db_cur = db_conn.cursor()

            db_cur.execute("""INSERT dataset_timeline_events(event_on, created_by, type, state, comment, dataset_id) VALUES(%(event_on)s, %(created_by)s, %(type)s, %(state)s, %(comment)s, %(dataset_id)s) RETURNING id;""",
                           {"event_on": self._timestamp, "created_by": self._user,
                            "type": self._event_type, "state": self._state,
                            "comment": self._text, "dataset_id": self._dataset_id})

            self._id = db_cur.fetchone()[0]

            db_conn.commit()
            psql.PostgreSQLConnection().returnConnection(db_conn)
        except Exception as err:
            if "db_conn" in locals():
                db_conn.rollback()  # fixme: cleaner way of doing this?
            if "db_cur" in locals():
                psql.PostgreSQLConnection().returnConnection(db_conn)
            raise err

    def __db_select(self):
        if self._id is None:
            raise dlib.ABCInstrumentError("No id (db_id) set for PostgreSQLDatasetTimelineEvent. Unable to perform SELECT.")

        try:
            db_conn = psql.PostgreSQLConnection().getConnection()
            db_cur = db_conn.cursor()

            db_cur.execute("SELECT event_on, created_by, type, state, comment, dataset_id FROM dataset_timeline_events WHERE id = %(db_id)s;", {"db_id": self._id})

            db_row = db_cur.fetchone()
            self._timestamp = db_row[0]
            self._user = db_row[1]
            self._event_type = db_row[2]
            self._state = db_row[3]
            self._text = db_row[4]
            self._dataset_id = db_row[5]

            psql.PostgreSQLConnection().returnConnection(db_conn)
        except Exception as err:
            if "db_cur" in locals():
                psql.PostgreSQLConnection().returnConnection(db_conn)
            raise err

    def read(self):
        self.__db_select()

    def write(self):
        if self._id is None:  # Question: Can we assume that? It should be 'always' True if only PostgreSQLInstruments classes are used.
            self.__db_insert()
        else:
            raise dlib.ABCTimelineError("No update implemented for PostgreSQLDatasetTimelineEvent yet!")

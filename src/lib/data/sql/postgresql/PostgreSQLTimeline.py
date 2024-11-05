from __future__ import annotations

from datetime import datetime
from typing import Dict, List

import psycopg2

import lib.data as dlib
import lib.data.sql.postgresql as psql

class PostgreSQLTimeline(dlib.ABCTimeline):

    @classmethod
    def add_new_dataset_timeline_event(cls, user: dlib.ABCUser | None, state: dlib.TimelineEventState, text: str | None,
                                       event_type: dlib.DatasetTimelineEventType, dataset_id: int | None,
                                       timestamp: datetime = datetime.now(tz=None),
                                       db_cur_session: psycopg2.cursor | None = None) -> PostgreSQLDatasetTimelineEvent:
        event = PostgreSQLDatasetTimelineEvent(db_id=None, timestamp=timestamp, user=user, state=state, text=text, event_type=event_type, dataset_id=dataset_id)
        event.write(db_cur_session=db_cur_session)
        return event

    @classmethod
    def objectify_with_dataset_label(cls, dataset_label: str, db_cur_session: psycopg2.cursor | None = None) -> List[PostgreSQLDatasetTimelineEvent]:
        events: List[PostgreSQLDatasetTimelineEvent] = []
        users: Dict[int, psql.PostgreSQLUser] = {}

        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("SELECT e.id, e.event_on, e.created_by, e.type, e.state, e.comment, e.dataset_id FROM dataset_timeline_events AS e "
                           "LEFT JOIN datasets AS d ON d.id = e.dataset_id"
                           "WHERE d.label = %(dataset_label)s ORDER BY e.event_on DESC;",
                           {"dataset_label": dataset_label})

            for db_row in db_cur:  # db_cur.rowcount  # db_cur.rowcount
                if db_row[2] not in users:
                    users[db_row[2]] = psql.PostgreSQLUser.objectify_with_id(db_row[2])  # ToDo: Improve Create / Receive user object by id

                events.append(PostgreSQLDatasetTimelineEvent(db_id=db_row[0], timestamp=db_row[1], user=users[db_row[2]],
                                                             state=db_row[4], text=db_row[5], event_type=db_row[3], dataset_id=db_row[6]))

        finally:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

        return events
        pass

    @classmethod
    def objectify_with_dataset_id(cls, dataset_id: int, db_cur_session: psycopg2.cursor | None = None) -> List[PostgreSQLDatasetTimelineEvent]:  # ToDo: merge with the objectify_with_dataset_label method
        events: List[PostgreSQLDatasetTimelineEvent] = []
        users: Dict[int, psql.PostgreSQLUser] = {}

        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("SELECT id, event_on, created_by, type, state, comment FROM dataset_timeline_events WHERE dataset_id = %(dataset_id)s ORDER BY event_on DESC;",
                           {"dataset_id": dataset_id})

            for db_row in db_cur:  # db_cur.rowcount  # db_cur.rowcount
                if db_row[2] not in users:
                    users[db_row[2]] = psql.PostgreSQLUser.objectify_with_id(db_row[2])  # ToDo: Improve Create / Receive user object by id

                events.append(PostgreSQLDatasetTimelineEvent(db_id=db_row[0], timestamp=db_row[1], user=users[db_row[2]],
                                                             state=db_row[4], text=db_row[5], event_type=db_row[3], dataset_id=dataset_id))

        finally:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

        return events


class PostgreSQLDatasetTimelineEvent(dlib.ABCDatasetTimelineEvent):
    def __db_insert(self, db_cur_session: psycopg2.cursor | None = None):
        if self._id:
            raise dlib.ABCTimelineError("Unable to perform database INSERT with PostgreSQLDatasetTimelineEvent that does already exist in database.")

        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("""INSERT INTO dataset_timeline_events(event_on, created_by, type, state, comment, dataset_id) VALUES(%(event_on)s, %(created_by)s, %(type)s, %(state)s, %(comment)s, %(dataset_id)s) RETURNING id;""",
                           {"event_on": self._timestamp, "created_by": self._user.get_id(),
                            "type": self._event_type, "state": self._state,
                            "comment": self._text, "dataset_id": self._dataset_id})

            self._id = db_cur.fetchone()[0]

            if db_conn:
                db_conn.commit()
        except Exception as err:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                db_conn.rollback()
            raise err
        finally:
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

    def __db_select(self, db_cur_session: psycopg2.cursor | None = None):
        if self._id is None:
            raise dlib.ABCInstrumentError("No id (db_id) set for PostgreSQLDatasetTimelineEvent. Unable to perform SELECT.")

        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
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

        finally:
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

    def read(self, db_cur_session: psycopg2.cursor | None = None):
        self.__db_select(db_cur_session = db_cur_session)

    def write(self, db_cur_session: psycopg2.cursor | None = None):
        if self._id is None:  # Question: Can we assume that? It should be 'always' True if only PostgreSQLInstruments classes are used.
            self.__db_insert(db_cur_session = db_cur_session)
        else:
            raise dlib.ABCTimelineError("No update implemented for PostgreSQLDatasetTimelineEvent yet!")

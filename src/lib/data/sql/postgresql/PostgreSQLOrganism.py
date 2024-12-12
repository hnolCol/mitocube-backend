from __future__ import annotations

from typing import Any, Tuple

import psycopg2

import lib.data as dlib
import lib.data.sql.postgresql as psql


class PostgreSQLOrganism(dlib.ABCOrganism):
    @staticmethod
    def __get_db_select_row(db_id: int | None = None, label: str | None = None,
                            db_cur_session: psycopg2.cursor | None = None) -> Tuple[Any]:
        if db_id is None and label is None:
            raise dlib.ABCInstrumentError("No id (db_id) nor label set for PostgreSQLInstrument. Unable to perform SELECT.")

        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            # if db_id:
            #     db_cur.execute("SELECT id, label, name, location, description, base64_image FROM instruments WHERE id = %(db_id)s;",
            #                    {"db_id": db_id})
            # else:
            #     db_cur.execute("SELECT id, label, name, location, description, base64_image FROM instruments WHERE label = %(label)s;",
            #                    {"label": label})

            if db_cur.rowcount != 1:
                raise dlib.ABCInstrumentError("Provided id or label does not match a instrument. Number of returned rows = {n}".format(n=db_cur.rownumber))

            db_row = db_cur.fetchone()

        finally:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

        return db_row

    def __db_insert(self, use_id: bool = False, db_cur_session: psycopg2.cursor | None = None):
        if self.does_exist():
            raise dlib.ABCInstrumentError("Unable to perform database INSERT with PostgreSQLInstrument that does already exist in database.")

        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            # if use_id:
            #     if self._id is None:
            #         raise dlib.ABCInstrumentError("No id (db_id) set for PostgreSQLInstrument. Unable to perform INSERT with assigned id.")

            #     db_cur.execute("""INSERT INTO instruments(id, label, name, location, description, base64_image)
            #                         VALUES(%(db_id)s, %(label)s, %(name)s, %(location)s, %(description)s, %(base64_image)s) RETURNING id;""",
            #                    {"db_id": self._id,
            #                     "label": self._label,
            #                     "location": self._location,
            #                     "base64_image": self._base64_image,  # Todo: Check if psycopg2.Binary(self._base64_image) is required
            #                     "name": self._name,
            #                     "description": self._description})
            # else:
            #     db_cur.execute("""INSERT INTO instruments(label, name, location, description, base64_image)
            #                         VALUES(%(label)s, %(name)s, %(location)s, %(description)s, %(base64_image)s) RETURNING id;""",
            #                    {"label": self._label,
            #                     "location": self._location,
            #                     "base64_image": self._base64_image,  # Todo: Check if psycopg2.Binary(self._base64_image) is required
            #                     "name": self._name,
            #                     "description": self._description})

            self._id = db_cur.fetchone()[0]

            if db_conn:
                db_conn.commit()
        except Exception as err:  # fixme: switch to psycopg 3 to be able to use with statements? https://github.com/psycopg/psycopg2/pull/367 https://www.psycopg.org/psycopg3/docs/advanced/pool.html#connection-pools
            if db_conn:
                db_conn.rollback()
            raise err
        finally:
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

    def __db_update(self, db_cur_session: psycopg2.cursor | None = None):
        if not self.does_exist():
            raise dlib.ABCInstrumentError("Unable to perform database UPDATE on postgreSQLInstrument that does not exist in database.")

        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            # db_cur.execute("UPDATE instruments SET label = %(label)s, name = %(name)s, location = %(location)s, base64_image = %(base64_image)s, description = %(description)s WHERE id = %(id)s;",
            #                {"id": self._id,
            #                 "label": self._label,
            #                 "location": self._location,
            #                 "base64_image": self._base64_image,
            #                 "name": self._name,
            #                 "description": self._description})

            if db_conn:
                db_conn.commit()
        except Exception as err:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                db_conn.rollback()
            raise err
        finally:
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

    @classmethod
    def objectify_with_id(cls, db_id: int) -> PostgreSQLInstrument:
        # db_row = PostgreSQLInstrument.__get_db_select_row(db_id = db_id)

        # return cls(db_id = db_id, label = db_row[1], name = db_row[2], location = db_row[3], description = db_row[4],
        #            base64_image = db_row[5])
        pass

    @classmethod
    def objectify_with_label(cls, label: str) -> PostgreSQLInstrument:
        # db_row = PostgreSQLInstrument.__get_db_select_row(label = label)

        # return cls(db_id = db_row[0], label = label, name = db_row[2], location = db_row[3], description = db_row[4],
        #            base64_image = db_row[5])
        pass

    def write_to_db(self, db_cur_session: psycopg2.cursor | None = None):
        self.__db_insert(use_id=False, db_cur_session=db_cur_session) if self._id is None else self.__db_update(db_cur_session=db_cur_session)

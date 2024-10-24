from __future__ import annotations

from typing import Any, Dict, List, Tuple

import psycopg2

import lib.data as dlib
import lib.data.sql.postgresql as psql


class PostgreSQLMetatext(dlib.ABCMetatext):

    @staticmethod
    def __get_db_select_row(dataset_id: int, tag: str, db_cur_session: psycopg2.cursor | None = None) -> Tuple[Any]:
        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("SELECT text FROM metatexts WHERE tag = %(tag)s AND dataset_id = %(db_id)s;",
                           {"dataset_id": dataset_id, "tag": tag})

            db_row = db_cur.fetchone()

        finally:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

        return db_row

    def __db_insert(self, db_cur_session: psycopg2.cursor | None = None):
        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("""INSERT INTO metatexts(dataset_id, tag, text) VALUES(%(dataset_id)s, %(tag)s, %(text)s);""",
                           {"dataset_id": self._dataset_id, "tag": self._tag, "text": self._text})

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
        db_row = PostgreSQLMetatext.__get_db_select_row(dataset_id=self._dataset_id, tag=self._tag, db_cur_session = db_cur_session)
        self._text = db_row[0]

    def __db_delete(self, db_cur_session: psycopg2.cursor | None = None):
        if self._tag is None or self._dataset_id is None:
            raise dlib.ABCMetatextError("No tag nor dataset_id set for PostgreSQLMetatext. Unable to perform a DELETE.")

        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("""DELETE FROM metatexts WHERE dataset_id = %(dataset_id)s AND tag = %(tag)s;""",
                           {"dataset_id": self._dataset_id, "tag": self._tag, "text": self._text})

            if db_conn:
                db_conn.commit()
        except Exception as err:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                db_conn.rollback()
            raise err
        finally:
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

    def __db_update(self, db_cur_session: psycopg2.cursor | None = None):
        if self._tag is None or self._dataset_id is None:
            raise dlib.ABCMetatextError("No tag or no dataset_id set for PostgreSQLMetatext. Unable to perform UPDATE.")

        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("""UPDATE metatexts SET text =  %(text)s WHERE dataset_id = %(dataset_id)s AND tag = %(tag)s;""",
                           {"dataset_id": self._dataset_id, "tag": self._tag, "text": self._text})

            if db_conn:
                db_conn.commit()
        except Exception as err:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                db_conn.rollback()
            raise err
        finally:
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

    @staticmethod
    def is_tag_used(dataset_id: int, tag: str, db_cur_session: psycopg2.cursor | None = None) -> bool:
        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("SELECT EXISTS(SELECT 1 FROM metatexts WHERE dataset_id=%(dataset_id)s AND tag=%(tag)s);", {"dataset_id": dataset_id, "tag": tag})
            does_exist = db_cur.fetchone()[0]

        finally:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

        return does_exist

    @classmethod
    def objectify_with_dataset_id(cls, dataset_id: int, db_cur_session: psycopg2.cursor | None = None) -> Dict[str, PostgreSQLMetatext]:
        metatexts: Dict[str,PostgreSQLMetatext] = {}

        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("SELECT tag, text FROM metatexts WHERE dataset_id = %(dataset_id)s;", {"dataset_id": dataset_id})

            for db_row in db_cur:  # db_cur.rowcount  # db_cur.rowcount
                metatexts[db_row[0]] = cls(dataset_id=dataset_id, tag=db_row[0], text=db_row[1])

        finally:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

        return metatexts

    def read(self, db_cur_session: psycopg2.cursor | None = None):
        self.__db_select(db_cur_session=db_cur_session)

    def write(self, db_cur_session: psycopg2.cursor | None = None):
        if self._text is None or len(self._text) < 1:
            self.__db_delete(db_cur_session=db_cur_session)
        elif PostgreSQLMetatext.is_tag_used(dataset_id = self._dataset_id, tag = self._tag):
            self.__db_update(db_cur_session=db_cur_session)
        else:
            self.__db_insert(db_cur_session = db_cur_session)

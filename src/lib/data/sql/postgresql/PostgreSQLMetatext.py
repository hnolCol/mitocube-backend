from __future__ import annotations

from typing import List, Self

import lib.data as dlib
import lib.data.sql.postgresql as psql


class PostgreSQLMetatext(dlib.ABCMetatext):

    # def __init__(self, is_in_database: bool = False, **kwargs):  # Fixme: Would love multiple constructors... what is the clean python alternative?
    #     super().__init__(**kwargs)  # Question: Why is this not working? dataset_id is missing as positional argument Exception

    def __init__(self, tag: str, text: str, dataset_id: int | None = None, is_in_database: bool = False):
        super().__init__(tag = tag, text = text, dataset_id = dataset_id)

        self._is_in_database: bool = is_in_database

    def __db_insert(self):
        try:
            db_conn = psql.PostgreSQLConnection().getConnection()
            db_cur = db_conn.cursor()

            db_cur.execute("""INSERT urls(dataset_id, tag, text) VALUES(%(dataset_id)s, %(tag)s, %(text)s);""",
                           {"dataset_id": self._dataset_id, "tag": self._tag, "text": self._text})

            db_conn.commit()
            psql.PostgreSQLConnection().returnConnection(db_conn)

            self._is_in_database = True
        except Exception as err:
            if "db_conn" in locals():
                db_conn.rollback()  # fixme: cleaner way of doing this?
            if "db_cur" in locals():
                psql.PostgreSQLConnection().returnConnection(db_conn)
            raise err

    def __db_select(self):
        try:
            db_conn = psql.PostgreSQLConnection().getConnection()
            db_cur = db_conn.cursor()

            db_cur.execute("SELECT text FROM metatexts WHERE tag = %(tag)s AND dataset_id = %(db_id)s;",
                           {"dataset_id": self._dataset_id, "tag": self._dataset_id})

            db_row = db_cur.fetchone()
            self._text = db_row[0]
            self._is_in_database = True

            psql.PostgreSQLConnection().returnConnection(db_conn)
        except Exception as err:
            if "db_cur" in locals():
                psql.PostgreSQLConnection().returnConnection(db_conn)
            raise err

    def __db_delete(self):
        if self._tag is None or self._dataset_id is None:
            raise dlib.ABCMetatextError("No tag nor dataset_id set for PostgreSQLMetatext. Unable to perform a DELETE.")

        try:
            db_conn = psql.PostgreSQLConnection().getConnection()
            db_cur = db_conn.cursor()

            db_cur.execute("""DELETE FROM metatexts WHERE dataset_id = %(dataset_id)s AND tag = %(tag)s;""",
                           {"dataset_id": self._dataset_id, "tag": self._tag, "text": self._text})

            db_conn.commit()
            psql.PostgreSQLConnection().returnConnection(db_conn)
        except Exception as err:
            if "db_conn" in locals():
                db_conn.rollback()  # fixme: cleaner way of doing this?
            if "db_cur" in locals():
                psql.PostgreSQLConnection().returnConnection(db_conn)
            raise err

    def __db_update(self, use_id: bool = False):
        if self._tag is None or self._dataset_id is None:
            raise dlib.ABCMetatextError("No tag nor dataset_id set for PostgreSQLMetatext. Unable to perform UPDATE.")

        try:
            db_conn = psql.PostgreSQLConnection().getConnection()
            db_cur = db_conn.cursor()

            db_cur.execute("""UPDATE metatexts SET text =  %(text)s WHERE dataset_id = %(dataset_id)s AND tag = %(tag)s;""",
                           {"dataset_id": self._dataset_id, "tag": self._tag, "text": self._text})

            db_conn.commit()
            psql.PostgreSQLConnection().returnConnection(db_conn)
        except Exception as err:
            if "db_conn" in locals():
                db_conn.rollback()  # fixme: cleaner way of doing this?
            if "db_cur" in locals():
                psql.PostgreSQLConnection().returnConnection(db_conn)
            raise err

    @classmethod
    def objectify_from_dataset_id(cls, database_id: int) -> List[dlib.ABCMetatext]:
        metatexts: List[PostgreSQLMetatext] = []

        try:
            db_conn = psql.PostgreSQLConnection().getConnection()
            db_cur = db_conn.cursor()

            db_cur.execute("SELECT tag, text FROM metatexts WHERE dataset_id = %(dataset_id)s;", {"dataset_id": database_id})

            for db_row in db_cur:  # db_cur.rowcount  # db_cur.rowcount
                metatexts.append(cls(dataset_id=database_id, tag=db_row[0], text=db_row[1], is_in_database=True))

            psql.PostgreSQLConnection().returnConnection(db_conn)
        except Exception as err:
            if "db_cur" in locals():
                psql.PostgreSQLConnection().returnConnection(db_conn)
            raise err

        return metatexts

    def read(self):
        self.__db_select()

    def write(self):
        if self._text is None or len(self._text) < 1:
            self.__db_delete()  #
        else:
            self.__db_update() if self._is_in_database else self.__db_insert()

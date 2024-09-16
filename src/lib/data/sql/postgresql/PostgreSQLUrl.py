from __future__ import annotations

from typing import List, Self

import psycopg2

import lib.data as dlib
import lib.data.sql.postgresql as psql


class PostgreSQLUrl(dlib.ABCUrl):

    def __db_insert(self, dataset_id: int, db_cur_session: psycopg2.cursor | None = None):
        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("""INSERT INTO dataset_urls(dataset_id, url) VALUES(%(dataset_id)s, %(url)s);""",
                           {"dataset_id": dataset_id, "url": self._url})

            if db_conn:
                db_conn.commit()
        except Exception as err:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                db_conn.rollback()
            raise err
        finally:
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)


    def append_to_dataset(self, dataset_id: int | None = None, db_cur_session: psycopg2.cursor | None = None):
        if dataset_id:
            self.__db_insert(dataset_id=dataset_id, db_cur_session=db_cur_session)
        elif self._dataset_id:
            self.__db_insert(dataset_id=self._dataset_id, db_cur_session=db_cur_session)
        else:
            raise dlib.ABCUrlError("No dataset id provided for URL, unable to append it to a dataset.")

    @classmethod
    def objectify_with_dataset_id(cls, dataset_id: int, db_cur_session: psycopg2.cursor | None = None) -> List[PostgreSQLUrl]:
        urls: List[PostgreSQLUrl] = []

        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("SELECT url FROM dataset_urls WHERE dataset_id = %(dataset_id)s;", {"dataset_id": dataset_id})

            for db_row in db_cur:  # db_cur.rowcount  # db_cur.rowcount
                urls.append(cls(dataset_id=dataset_id, url=db_row[0]))

        finally:
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

        return urls

    @classmethod
    def remove_all_from_dataset(cls, dataset_id: int, db_cur_session: psycopg2.cursor | None = None) :
        urls: List[PostgreSQLUrl] = []

        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("DELETE FROM dataset_urls WHERE dataset_id = %(dataset_id)s;", {"dataset_id": dataset_id})

            if db_conn:
                db_conn.commit()
        except Exception as err:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                db_conn.rollback()
            raise err
        finally:
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

        return urls

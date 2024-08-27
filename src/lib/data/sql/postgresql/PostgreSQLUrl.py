from __future__ import annotations

from typing import List, Self

import lib.data as dlib
import lib.data.sql.postgresql as psql


class PostgreSQLUrl(dlib.ABCUrl):

    def __db_insert(self):
        try:
            db_conn = psql.PostgreSQLConnection().getConnection()
            db_cur = db_conn.cursor()

            db_cur.execute("""INSERT urls(dataset_id, url) VALUES(%(dataset_id)s, %(url)s);""",
                           {"dataset_id": self._dataset_id, "url": self._url})

            db_conn.commit()
            psql.PostgreSQLConnection().returnConnection(db_conn)
        except Exception as err:
            if "db_conn" in locals():
                db_conn.rollback()  # fixme: cleaner way of doing this?
            if "db_cur" in locals():
                psql.PostgreSQLConnection().returnConnection(db_conn)
            raise err

    def append_to_dataset(self):
        self.__db_insert()

    @classmethod
    def objectify_with_dataset_id(cls, dataset_id: int) -> List[dlib.ABCUrl]:
        urls: List[PostgreSQLUrl] = []

        try:
            db_conn = psql.PostgreSQLConnection().getConnection()
            db_cur = db_conn.cursor()

            db_cur.execute("SELECT url FROM urls WHERE dataset_id = %(dataset_id)s;", {"dataset_id": dataset_id})

            for db_row in db_cur:  # db_cur.rowcount  # db_cur.rowcount
                urls.append(cls(dataset_id=dataset_id, url=db_row[0]))

            psql.PostgreSQLConnection().returnConnection(db_conn)
        except Exception as err:
            if "db_cur" in locals():
                psql.PostgreSQLConnection().returnConnection(db_conn)  # ToDo: Find a better solution, like with
            raise err

        return urls

    @classmethod
    def remove_all_from_dataset(cls, dataset_id: int) :
        urls: List[PostgreSQLUrl] = []

        try:
            db_conn = psql.PostgreSQLConnection().getConnection()
            db_cur = db_conn.cursor()

            db_cur.execute("DELETE FROM urls WHERE dataset_id = %(dataset_id)s;", {"dataset_id": dataset_id})

            db_conn.commit()
            psql.PostgreSQLConnection().returnConnection(db_conn)
        except Exception as err:
            if "db_cur" in locals():
                psql.PostgreSQLConnection().returnConnection(db_conn)
            raise err

        return urls

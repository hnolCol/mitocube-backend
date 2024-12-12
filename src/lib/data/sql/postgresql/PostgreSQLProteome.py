from __future__ import annotations

from typing import Any, Tuple

import psycopg2

import lib.data as dlib
import lib.data.sql.postgresql as psql


class PostgreSQLProteome(dlib.ABCProteome):
    @staticmethod
    def __get_db_select_row(db_id: int | None = None, proteome_id: str | None = None,
                            db_cur_session: psycopg2.cursor | None = None) -> Tuple[Any]:
        if db_id is None and proteome_id is None:
            raise dlib.ABCProjectError("No id (db_id) nor proteome_id set for PostgreSQLProteome. Unable to perform SELECT.")

        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            if db_id:
                db_cur.execute("SELECT id, proteome_id, organism_id, status, comment WHERE id = %(db_id)s;",
                               {"db_id": db_id})
            else:
                db_cur.execute("SELECT id, proteome_id, organism_id, status, comment WHERE proteome_id = %(label)s;",
                               {"proteome_id": proteome_id})

            if db_cur.rowcount != 1:
                raise dlib.ABCProjectError("Provided ids does not match a proteome. Number of returned rows = {n}".format(n=db_cur.rownumber))

            db_row = db_cur.fetchone()

        finally:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

        return db_row

    def __db_insert(self, db_cur_session: psycopg2.cursor | None = None):
        if self._id is None:
            raise dlib.ABCProjectError("Unable to perform database INSERT with PostgreSQLProteome that does already exist in database.")

        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("""INSERT INTO proteomes(proteome_id, organism_id, status, comment)
                                VALUES(%(proteome_id)s, %(organism_id)s, %(status)s, %(comment)s) RETURNING id;""",
                           {"proteome_id": self._proteome_id,
                            "organism_id": self._organism.get_id(),
                            "status": self._status,
                            "comment": self._comment})

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
        if self._id is None:
            raise dlib.ABCProjectError("Unable to perform database UPDATE on PostgreSQLProteome that does not exist in database.")

        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("""UPDATE public.proteomes 
                                SET proteome_id=%(proteome_id)s), organism_id=%(organism_id)s, status=%(status)s, comment=%(comment)s 
                                WHERE id = %(id)s;""",
                           {"id": self._id,
                            "proteome_id": self._proteome_id,
                            "organism_id": self._organism,
                            "status": self._status,
                            "comment": self._comment})

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
    def objectify_with_id(cls, db_id: int) -> PostgreSQLProteome:
        db_row = PostgreSQLProteome.__get_db_select_row(db_id = db_id)

        return cls(db_id = db_id, proteome_id = db_row[1],
                   organism = psql.PostgreSQLOrganism.objectify_with_id(db_id = db_row[2]),
                   status = db_row[3], comment = db_row[4])

    @classmethod
    def objectify_with_proteome_id(cls, proteome_id: str) -> PostgreSQLProteome:
        db_row = PostgreSQLProteome.__get_db_select_row(proteome_id = proteome_id)

        return cls(db_id = db_row[0], proteome_id = proteome_id,
                   organism = psql.PostgreSQLOrganism.objectify_with_id(db_id = db_row[2]),
                   status = db_row[3], comment = db_row[4])

    def write_to_db(self, db_cur_session: psycopg2.cursor | None = None):
        self.__db_insert(db_cur_session=db_cur_session) if self._id is None else self.__db_update(db_cur_session=db_cur_session)

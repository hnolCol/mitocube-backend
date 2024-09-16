from __future__ import annotations

from typing import Any, Tuple

import psycopg2

import lib.data as dlib
import lib.data.sql.postgresql as psql


class PostgreSQLProject(dlib.ABCProject):

    @staticmethod
    def __get_db_select_row(db_id: int | None = None, db_cur_session: psycopg2.cursor | None = None) -> Tuple[Any]:

        if db_id is None:
            raise dlib.ABCProjectError("No id (db_id) set for PostgreSQLProject. Unable to perform SELECT.")

        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("SELECT id, title, description FROM projects WHERE id = %(db_id)s;", {"db_id": db_id})

            db_row = db_cur.fetchone()

        finally:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

        return db_row

    def __db_insert(self, use_id: bool = False, write_datasets: bool = False, db_cur_session: psycopg2.cursor | None = None):  # ToDo: Implement write_datasets
        if self.does_exist():
            raise dlib.ABCProjectError("Unable to perform database INSERT with Project that does already exist in database.")

        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            if use_id :
                if self._id is None:
                    raise dlib.ABCProjectError("No id (db_id) set for Project. Unable to perform INSERT with assigned id.")

                db_cur.execute("INSERT INTO projects(id, title, description) VALUES(%(db_id)s, %(title)s, %(description)s) RETURNING id;",
                               {"db_id": self._id, "title": self._title, "description": self._description})
            else:
                db_cur.execute("INSERT INTO projects(title, description) VALUES(%(title)s, %(description)s) RETURNING id;",
                               {"title": self._title, "description": self._description})

            self._id = db_cur.fetchone()[0]

            if write_datasets:
                if self._datasets is None:
                    raise dlib.ABCProjectError("No datasets attached to PostgreSQLProject. Unable to add datasets!")
                elif len(self._datasets) < 1:
                    raise dlib.ABCProjectError("Empty list of datasets attached to PostgreSQLProject. Unable to add datasets!")

                raise dlib.ABCProjectError("Writing attached datasets is not implemented yet!")

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
        db_row = PostgreSQLProject.__get_db_select_row(self._id, db_cur_session = db_cur_session)

        self._id = db_row[0]
        self._title = db_row[1]
        self._description = db_row[2]

    def __db_update(self, db_cur_session: psycopg2.cursor | None = None):
        if not self.does_exist():
            raise dlib.ABCProjectError("Unable to perform database UPDATE on Project that does not exist in database.")

        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("UPDATE projects SET title = %(title)s, description = %(description)s WHERE id = %(id)s;",
                           {"id": self._id, "title": self._title, "description": self._description})

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
    def objectify_with_id(cls, db_id: int, fetch_datasets: bool = False) -> PostgreSQLProject:
        db_row = PostgreSQLProject.__get_db_select_row(db_id)

        obj = cls(db_id=db_id, title=db_row[1], description=db_row[2], datasets=None)  # : List[dlib.ABCDataset] | None = None

        if fetch_datasets:
            raise dlib.ABCProjectError("Fetching linked datasets is not implemented yet!")  # ToDo: add argument / implement fetch datasets and do it here!

        return obj

    def does_exist(self, db_cur_session: psycopg2.cursor | None = None):
        if self._id is None:
            return False
        else:
            return PostgreSQLProject.does_exist_with_id(self._id, db_cur_session = db_cur_session)

    @staticmethod
    def does_exist_with_id(db_id: int, db_cur_session: psycopg2.cursor | None = None) -> bool:
        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("SELECT EXISTS(SELECT 1 FROM projects WHERE id=%(id)s", {"id": db_id})
            does_exist = db_cur.fetchone()[0]

        finally:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

        return does_exist

    def read(self, fetch_datasets: bool = False, db_cur_session: psycopg2.cursor | None = None):
        self.__db_select(db_cur_session = db_cur_session)

        if fetch_datasets:
            raise dlib.ABCProjectError("Fetching datasets for a project is not implemented yet.")  # ToDo: implement fetch_datasets for projects
        else:
            self._datasets = None

    def write(self, write_datasets: bool = False, db_cur_session: psycopg2.cursor | None = None):
        self.__db_insert(use_id=False, db_cur_session=db_cur_session) if self._id is None else self.__db_update(db_cur_session=db_cur_session)

        if write_datasets:
            raise dlib.ABCProjectError("Writing/Creating datasets for a project is not implemented yet.")  # ToDo: implement write_datasets for projects

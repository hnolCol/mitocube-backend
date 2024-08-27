from __future__ import annotations

import lib.data as dlib
import lib.data.sql.postgresql as psql


class PostgreSQLProject(dlib.ABCProject):
    
    # def __init__(self, db_id: int, title: str, description: str | None, datasets: List[dlib.ABCDataset] | None = None):
    def __init__(self, **kwargs):  # FixMe: Would love multiple constructors... what is the clean python alternative?
        super().__init__(**kwargs)
        # super().__init__(db_id=-1, title="str", description:="str", datasets=None) 

    # @staticmethod

    def __db_insert(self, use_id: bool = False, write_datasets: bool = False):  # ToDo: Implement write_datasets
        if self.does_exist():
            raise dlib.ABCProjectError("Unable to perform database INSERT with Project that does already exist in database.")

        try:
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

            db_conn.commit()
            psql.PostgreSQLConnection().returnConnection(db_conn)
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

            if self._id is None:
                raise dlib.ABCProjectError("No id (db_id) set for PostgreSQLProject. Unable to perform SELECT.")

            db_cur.execute("SELECT id, title, description FROM projects WHERE id = %(db_id)s;", {"db_id": self._id})

            db_row = db_cur.fetchone()
            self._id = db_row[0]
            self._title = db_row[1]
            self._description = db_row[2]

            psql.PostgreSQLConnection().returnConnection(db_conn)
        except Exception as err:
            if "db_cur" in locals():
                psql.PostgreSQLConnection().returnConnection(db_conn)  # fixme: cleaner way of doing this?
            raise err

    def __db_update(self):
        if not self.does_exist():
            raise dlib.ABCProjectError("Unable to perform database UPDATE on Project that does not exist in database.")

        try:
            db_conn = psql.PostgreSQLConnection().getConnection()
            db_cur = db_conn.cursor()

            db_cur.execute("UPDATE projects SET title = %(title)s, description = %(description)s WHERE id = %(id)s;",
                           {"id": self._id, "title": self._title, "description": self._description})

            db_conn.commit()
            psql.PostgreSQLConnection().returnConnection(db_conn)
        except Exception as err:
            if "db_conn" in locals():
                db_conn.rollback()  # Fixme: cleaner way of doing this?
            if "db_cur" in locals():
                psql.PostgreSQLConnection().returnConnection(db_conn)
            raise err

    @classmethod
    def create_from_id(cls, db_id: int, fetch_datasets: bool = False) -> PostgreSQLProject:  # ToDo: inherit it from the parent class, is it possible to overwrite return type? any restrictions form parent class?
        obj = cls(db_id = db_id)  # Fixme: This will cause an exception since not all argument are served
        obj.read()

        if fetch_datasets:
            raise dlib.ABCProjectError("Fetching linked datasets is not implemented yet!")  # ToDo: add argument to fetch datasets and do it here!

        return obj

    def does_exist(self):
        if self._id is None:
            return False
        else:
            return PostgreSQLProject.does_exist_with_id(self._id)

    @staticmethod
    def does_exist_with_id(db_id: int) -> bool:
        try:
            db_conn = psql.PostgreSQLConnection().getConnection()
            db_cur = db_conn.cursor()

            db_cur.execute("SELECT EXISTS(SELECT 1 FROM projects WHERE id=%(id)s", {"id": db_id})
            does_exist = db_cur.fetchone()[0]

            psql.PostgreSQLConnection().returnConnection(db_conn)
        except Exception as err:
            if "db_cur" in locals():
                psql.PostgreSQLConnection().returnConnection(db_conn)  # fixme: cleaner way of doing this?
            raise err

        return does_exist

    def read(self, fetch_datasets: bool = False):
        self.__db_select()

        if fetch_datasets:
            raise dlib.ABCProjectError(
                "Fetching datasets for a project is not implemented yet.")  # ToDo: implement fetch_datasets for projects
        else:
            self._datasets = None

    def write(self, write_datasets: bool = False):
        self.__db_insert(use_id=False) if self._id is None else self.__db_update()

        if write_datasets:
            raise dlib.ABCProjectError("Writing/Creating datasets for a project is not implemented yet.")  # ToDo: implement write_datasets for projects

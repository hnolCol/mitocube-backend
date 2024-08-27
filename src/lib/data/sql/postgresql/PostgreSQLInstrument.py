from __future__ import annotations

import lib.data as dlib
import lib.data.sql.postgresql as psql


class PostgreSQLInstrument(dlib.ABCInstrument):
    # def __init__(self, db_id: int | None, label: str, name: str, location: str | None, description: str | None, base64_image: str | None):
    def __init__(self, **kwargs):  # FixMe: Would love multiple constructors... what is the clean python alternative?
        super().__init__(**kwargs)

    def __db_insert(self, use_id: bool = False):
        if self.does_exist():
            raise dlib.ABCInstrumentError("Unable to perform database INSERT with PostgreSQLInstrument that does already exist in database.")

        try:
            db_conn = psql.PostgreSQLConnection().getConnection()
            db_cur = db_conn.cursor()

            # Fixme: Solution for better control to return returning the connection to the pool required. Below with statements wont't work... i think
            # with db_conn:  # https://github.com/psycopg/psycopg2/pull/367
            #     with db_conn.cursor() as db_cur:
            # ToDo: Test the below way to have a clean pool / connection / return on exception routine.
            # with psql.PostgreSQLConnection().getPoolObject().connection() as db_conn:  # https://www.psycopg.org/psycopg3/docs/advanced/pool.html#connection-pools
            #      with db_conn.cursor() as db_cur:

            if use_id:
                if self._id is None:
                    raise dlib.ABCInstrumentError("No id (db_id) set for p"
                                             "PostgreSQLInstrument. Unable to perform INSERT with assigned id.")

                db_cur.execute("""INSERT INTO instruments(id, label, name, location, description) 
                                    VALUES(%(db_id)s, %(title)s, %(description)s) RETURNING id;""",
                               {"db_id": self._id,
                                "label": self._label,
                                "location": self._location,
                                "base64_image": self._base64_image,  # Todo: Check if psycopg2.Binary(self._base64_image) is required
                                "name": self._name,
                                "description": self._description})
            else:
                db_cur.execute("""INSERT instruments(id, label, name, location, description) 
                                    VALUES(%(title)s, %(description)s) RETURNING id;""",
                               {"label": self._label,
                                "location": self._location,
                                "base64_image": self._base64_image,  # Todo: Check if psycopg2.Binary(self._base64_image) is required
                                "name": self._name,
                                "description": self._description})

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
            raise dlib.ABCInstrumentError("No id (db_id) set for PostgreSQLInstrument. Unable to perform SELECT.")

        try:
            db_conn = psql.PostgreSQLConnection().getConnection()
            db_cur = db_conn.cursor()

            db_cur.execute("SELECT id, label, name, location, description, base64_image FROM instruments WHERE id = %(db_id)s;", {"db_id": self._id})

            db_row = db_cur.fetchone()
            self._id = db_row[0]
            self._label = db_row[1]
            self._name = db_row[2]
            self._location = db_row[3]
            self._description = db_row[4]
            self._base64_image = db_row[5]

            psql.PostgreSQLConnection().returnConnection(db_conn)
        except Exception as err:
            if "db_cur" in locals():
                psql.PostgreSQLConnection().returnConnection(db_conn)
            raise err

    def __db_update(self, use_id: bool = False):
        if not self.does_exist():
            raise dlib.ABCInstrumentError("Unable to perform database UPDATE on postgreSQLInstrument that does not exist in database.")

        try:
            db_conn = psql.PostgreSQLConnection().getConnection()
            db_cur = db_conn.cursor()

            db_cur.execute("UPDATE instruments SET label = %(label)s, name = %(name)s, location = %(location)s, base64_image = %(base64_image)s, description = %(description)s WHERE id = %(id)s;",
                           {"id": self._id,
                            "label": self._label,
                            "location": self._location,
                            "base64_image": self._base64_image,
                            "name": self._name,
                            "description": self._description})

            db_conn.commit()
            psql.PostgreSQLConnection().returnConnection(db_conn)
        except Exception as err:
            if "db_conn" in locals():
                db_conn.rollback()  # fixme: cleaner way of doing this?
            if "db_cur" in locals():
                psql.PostgreSQLConnection().returnConnection(db_conn)
            raise err

    @classmethod
    def create_from_id(cls, db_id: int) -> PostgreSQLInstrument:  # ToDo: inherit it from the parent class, is it possible to overwrite return type? any restrictions form parent class?
        obj = cls(db_id = db_id)  # Fixme: This will cause an exception since not all argument are served
        obj.read()

        return obj

    def does_exist(self):
        if self._id is None:
            return False
        else:
            return PostgreSQLInstrument.does_exist_with_id(self._id)

    @staticmethod
    def does_exist_with_id(db_id: int) -> bool:
        try:
            db_conn = psql.PostgreSQLConnection().getConnection()
            db_cur = db_conn.cursor()

            db_cur.execute("SELECT EXISTS(SELECT 1 FROM instruments WHERE id=%(id)s", {"id": db_id})
            does_exist = db_cur.fetchone()[0]

            psql.PostgreSQLConnection().returnConnection(db_conn)
        except Exception as err:
            if "db_conn" in locals():
                psql.PostgreSQLConnection().returnConnection(db_conn)  # fixme: cleaner way of doing this?
            raise err

        return does_exist

    def read(self):
        self.__db_select()

    def write(self):
        self.__db_insert(use_id=False) if self._id is None else self.__db_update()

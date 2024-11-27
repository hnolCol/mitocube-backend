from __future__ import annotations

from typing import Any, Dict, List, Tuple, Self

import psycopg2

import lib.data as dlib
import lib.data.sql.postgresql as psql


class PostgreSQLTraitNode(dlib.ABCTraitNode):
    def __db_insert(self, db_cur_session: psycopg2.cursor | None = None):
        if self._id is not None:
            raise dlib.ABCAttributeError("Unable to perform database INSERT with PostgreSQLTraitNode that does already exist in database.")

        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("INSERT INTO trait_nodes (trait_id, parent_node_id, name, trait_value) VALUES (%(trait_id)s, %(parent_node_id)s, %(name)s, %(trait_value)s) RETURNING id;",
                           {"trait_id": self._trait.get_id(),
                            "parent_node_id": self._parent_node._id if self._parent_node else None,
                            "name": self._name,
                            "trait_value": self._value})

            db_row = db_cur.fetchone()
            self._id = db_row

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
        if self._id is None:
            raise dlib.ABCAttributeError("No set ID for PostgreSQLTrait. Unable to perform UPDATE.")

        # if not self.does_exist():  # ToDo: Implement
        #     raise dlib.ABCAttributeError("Unable to perform database UPDATE on PostgreSQLTrait that does not exist in database.")

        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("UPDATE trait_nodes SET name = %(name)s, trait_value = %(trait_value)s, "
                           "parent_node_id = %(parent_node_id)s, trait_id = %(trait_id)s WHERE id = %(db_id)s;",
                           {"db_id": self._id, "name": self._name, "trait_value": self._value,
                            "parent_node_id": self._parent_node, "trait_id": self._trait})

            if db_conn:
                db_conn.commit()
        except Exception as err:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                db_conn.rollback()
            raise err
        finally:
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

    def __db_delete(self, db_cur_session: psycopg2.cursor | None = None):
        if self._id is None:
            raise dlib.ABCAttributeError("No set ID for PostgreSQLTrait. Unable to perform DELETE.")

        # if not self.does_exist():  # ToDo: Implement
        #     raise dlib.ABCAttributeError("Unable to perform database UPDATE on PostgreSQLTrait that does not exist in database.")

        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("DELETE FROM trait_nodes WHERE id=%(db_id)s;", {"db_id": self._id})
            self._id = None

            if db_conn:
                db_conn.commit()
        except Exception as err:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                db_conn.rollback()
            raise err
        finally:
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

    def add_to_dataset_id(self, dataset_id: int, db_cur_session: psycopg2.cursor | None = None):
        db_conn = None
        db_cur = db_cur_session

        if self._id is None:
            raise dlib.ABCAttributeError("Unable to attach a TraitNode that does not exist in the database to a dataset.")

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("INSERT INTO nm_traits_datasets (trait_node_id, dataset_id) VALUES (%(trait_id)s, %(dataset_id)s);",
                           {"trait_node_id": self._id, "dataset_id": dataset_id})
            db_conn.commit()

        finally:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

    def add_to_sample_id(self, sample_id: int, db_cur_session: psycopg2.cursor | None = None):
        db_conn = None
        db_cur = db_cur_session

        if self._id is None:
            raise dlib.ABCAttributeError("Unable to attach a TraitNode that does not exist in the database to a sample.")

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("INSERT INTO nm_traits_samples (trait_node_id, sample_id) VALUES (%(trait_node_id)s, %(sample_id)s);",
                           {"trait_node_id": self._id, "sample_id": sample_id})
            if db_conn:
                db_conn.commit()
        except Exception as err:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                db_conn.rollback()
            raise err
        finally:
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

    def remove_from_dataset_id(self, dataset_id: int, db_cur_session: psycopg2.cursor | None = None):
        db_conn = None
        db_cur = db_cur_session

        if self._id is None:
            raise dlib.ABCAttributeError("Unable to remove a TraitNode that does not exist in the database from a dataset.")

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("DELETE FROM nm_traits_datasets WHERE trait_node_id=%(trait_node_id)s AND dataset_id=%(dataset_id)s;",
                           {"trait_node_id": self._id, "dataset_id": dataset_id})
            if db_conn:
                db_conn.commit()
        except Exception as err:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                db_conn.rollback()
            raise err
        finally:
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

    def remove_from_sample_id(self, sample_id: int, db_cur_session: psycopg2.cursor | None = None):
        db_conn = None
        db_cur = db_cur_session

        if self._id is None:
            raise dlib.ABCAttributeError("Unable to remove a TraitNode that does not exist in the database from a sample.")

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("DELETE FROM nm_traits_samples WHERE trait_node_id=%(trait_node_id)s AND sample_id=%(sample_id)s;",
                           {"trait_node_id": self._id, "sample_id": sample_id})
            if db_conn:
                db_conn.commit()
        except Exception as err:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                db_conn.rollback()
            raise err
        finally:
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

    def write_to_db(self, db_cur_session: psycopg2.cursor | None = None):
        self.__db_insert(db_cur_session = db_cur_session) if self._id is None else self.__db_update(db_cur_session = db_cur_session)

    def remove_from_db(self, db_cur_session: psycopg2.cursor | None = None):
        self.__db_delete(db_cur_session = db_cur_session)

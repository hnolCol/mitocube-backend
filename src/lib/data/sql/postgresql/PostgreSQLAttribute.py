from __future__ import annotations

from typing import Any, Dict, Tuple, List

import psycopg2

import lib.data as dlib
import lib.data.sql.postgresql as psql


class PostgreSQLAttribute(dlib.ABCAttribute):
    def __db_insert(self, db_cur_session: psycopg2.cursor | None = None):

        if self._id is not None:
            raise dlib.ABCAttributeError("Unable to perform database INSERT with PostgreSQLAttribute that does already exist in database.")
        elif PostgreSQLAttribute.does_tag_exist(tag = self._tag):
            raise dlib.ABCAttributeError("Unable to perform database INSERT. PostgreSQLAttribute, tag '{tag}' does already exist in database.".format(tag = self._tag))

        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()
            db_cur.execute("""INSERT INTO attributes(parent_id, tag, text, priority, allow_as_filter, allow_for_dataset, 
                                        allow_for_genotype, allow_for_performance, allow_for_sample, allow_trait_values, required_for_dataset_state,
                                        values_are_feature_labels, values_are_genotype_labels, values_are_numeric) 
                                    VALUES (%(parent_id)s, %(tag)s, %(text)s, %(priority)s, %(allow_as_filter)s, 
                                        %(allow_for_dataset)s, %(allow_for_genotype)s, %(allow_for_performance)s, 
                                        %(allow_for_sample)s, %(allow_trait_values)s, %(required_for_dataset_state)s,
                                        %(values_are_feature_labels)s, %(values_are_genotype_labels)s, %(values_are_numeric)s) RETURNING id;""",
                           {"parent_id": self._parent.get_id() if self._parent is not None else None,
                            "tag": self._tag,
                            "text": self._text,
                            "priority": self._priority,
                            "allow_as_filter": self._allow_as_filter,
                            "allow_for_dataset": self._allow_for_dataset,
                            "allow_for_genotype": self._allow_for_genotype,
                            "allow_for_performance": self._allow_for_performance,
                            "allow_for_sample": self._allow_for_sample,
                            "allow_trait_values": self._allow_trait_values,
                            "required_for_dataset_state": self._required_for_dataset_state,
                            "values_are_feature_labels": self._values_are_feature_labels,
                            "values_are_genotype_labels": self._values_are_genotype_labels,
                            "values_are_numeric": self._values_are_numeric})

            db_row = db_cur.fetchone()
            self._id = db_row[0]

            if db_conn:
                db_conn.commit()
        except Exception as err:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                db_conn.rollback()
            raise err
        finally:
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

    def __db_select(self, db_cur_session: psycopg2.cursor | None = None):  # ToDo: Update
        db_row = PostgreSQLAttribute.__get_db_select_row(db_id=self._id, tag=self._tag, db_cur_session=db_cur_session)

        self._id = db_row[0]
        self._parent = PostgreSQLAttribute.objectify_with_id(db_id = db_row[2], db_cur_session = db_cur_session) if db_row[2] else None
        self._tag = db_row[2]
        self._text = db_row[3]
        self._priority = db_row[4]
        self._allow_as_filter = db_row[5]
        self._allow_for_dataset = db_row[6]
        self._allow_for_genotype = db_row[7]
        self._allow_for_performance = db_row[8]
        self._allow_for_sample = db_row[9]
        self._allow_trait_values = db_row[10]
        self._required_for_dataset_state = db_row[11]
        self._values_are_feature_labels = db_row[12]
        self._values_are_genotype_labels = db_row[13]
        self._values_are_numeric = db_row[14]

    def __db_update(self, db_cur_session: psycopg2.cursor | None = None):
        if not self.does_exist():  # ToDo: Implement
            raise dlib.ABCAttributeError("Unable to perform database UPDATE on PostgreAttribute that does not exist in database.")

        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("""UPDATE attributes SET 
                                    parent_id = %(parent_id)s, tag = %(tag)s, text = %(text)s, priority = %(priority)s,
                                    required_for_dataset_state = %(required_for_dataset_state)s, 
                                    allow_as_filter = %(allow_as_filter), allow_for_dataset = %(allow_for_dataset)s, 
                                    allow_for_genotype = %(allow_for_genotype)s, allow_for_performance = %(allow_for_performance)s, 
                                    allow_for_sample = %(allow_for_sample)s, allow_trait_values = %(allow_trait_values)s, 
                                    values_are_feature_labels = %(values_are_feature_labels)s, 
                                    values_are_genotype_labels = %(values_are_genotype_labels)s, 
                                    values_are_numeric = %(values_are_numeric)s 
                                WHERE id = %(db_id)s;""",
                           {"db_id": self._id,
                            "parent_id": self._parent.get_id() if self._parent is not None else None,
                            "tag": self._tag, "text": self._text, "priority": self._priority,
                            "allow_as_filter": self._allow_as_filter,
                            "allow_for_dataset": self._allow_for_dataset,
                            "allow_for_genotype": self._allow_for_genotype,
                            "allow_for_performance": self._allow_for_performance,
                            "allow_for_sample": self._allow_for_sample,
                            "allow_trait_values": self._allow_trait_values,
                            "required_for_dataset_state": self._required_for_dataset_state,
                            "values_are_feature_labels": self._values_are_feature_labels,
                            "values_are_genotype_labels": self._values_are_genotype_labels,
                            "values_are_numeric": self._values_are_numeric})

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
    def __get_db_select_row(db_id: int | None = None, tag: str | None = None, db_cur_session: psycopg2.cursor | None = None) -> Tuple[Any]:
        if db_id is None and tag is None:
            raise dlib.ABCAttributeError("Neither id (db_id) nor tag set for PostgreSQLAttribute. Unable to perform SELECT.")

        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            if db_id is None:
                db_cur.execute("""SELECT id, parent_id, tag, text, priority, allow_as_filter, 
                        allow_for_dataset, allow_for_genotype, allow_for_performance, allow_for_sample, allow_trait_values, required_for_dataset_state,
                        values_are_feature_labels, values_are_genotype_labels, values_are_numeric 
                    FROM attributes WHERE tag = %(tag)s;""", {"tag": tag})
            else:
                db_cur.execute("""SELECT id, parent_id, tag, text, priority, allow_as_filter, 
                        allow_for_dataset, allow_for_genotype, allow_for_performance, allow_for_sample, allow_trait_values, required_for_dataset_state,
                        values_are_feature_labels, values_are_genotype_labels, values_are_numeric 
                    FROM attributes WHERE id = %(db_id)s;""", {"db_id": db_id})

            if db_cur.rowcount != 1:
                raise dlib.ABCAttributeNotFoundError("Provided id nor name does not match a single Attribute. Number of returned rows = {n}".format(n=db_cur.rownumber))

            db_row = db_cur.fetchone()
        finally:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

        return db_row

    @staticmethod
    def get_all_attributes(db_cur_session: psycopg2.cursor | None = None) -> Dict[int, PostgreSQLAttribute]:

        db_conn = None
        db_cur = db_cur_session

        attributes: Dict[int, PostgreSQLAttribute] = {}

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("""SELECT id, parent_id, tag, text, priority, allow_as_filter, 
                                allow_for_dataset, allow_for_genotype, allow_for_performance, 
                                allow_for_sample, allow_trait_values, required_for_dataset_state, 
                                values_are_feature_labels, values_are_genotype_labels, values_are_numeric 
                            FROM attributes ORDER by id ASC;""")

            db_rows = db_cur.fetchall()

            for db_row in db_rows:
                attributes[db_row[0]] = PostgreSQLAttribute(db_id = db_row[0],
                                                            parent_attribute = attributes[db_row[1]] if db_row[1] else None,
                                                            tag = db_row[2], text = db_row[3],
                                                            priority = db_row[4],
                                                            allow_as_filter = db_row[5],
                                                            allow_for_dataset = db_row[6],
                                                            allow_for_genotype = db_row[7],
                                                            allow_for_performance = db_row[8],
                                                            allow_trait_values = db_row[10],
                                                            allow_for_sample = db_row[9],
                                                            required_for_dataset_state = db_row[11],
                                                            values_are_feature_labels = db_row[12],
                                                            values_are_genotype_labels = db_row[13],
                                                            values_are_numeric = db_row[14])

        finally:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

        # attributes = Dict[str, PostgreSQLAttribute] = {obj.get_tag():obj for key, obj in attributes.items()}
        return attributes

    @staticmethod
    def does_tag_exist(tag: str, db_cur_session: psycopg2.cursor | None = None) -> bool:
        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("SELECT EXISTS(SELECT 1 FROM attributes WHERE tag=%(tag)s);", {"tag": tag})
            does_exist = db_cur.fetchone()[0]

        finally:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

        return does_exist

    @classmethod
    def objectify_with_id(cls, db_id: int, db_cur_session: psycopg2.cursor | None = None) -> PostgreSQLAttribute:
        db_row = PostgreSQLAttribute.__get_db_select_row(db_id = db_id, db_cur_session = db_cur_session)

        # Question: catch_parent = catch_parent or = False? Latter would prevent a possible circular import / endless loop
        return cls(parent_attribute = PostgreSQLAttribute.objectify_with_id(db_row[1]) if db_row[1] else None,
                   tag = db_row[2], text = db_row[3], priority = db_row[4], db_id = db_row[0],
                   allow_as_filter = db_row[5], allow_for_dataset = db_row[6], allow_for_genotype = db_row[7],
                   allow_for_performance = db_row[8], allow_for_sample = db_row[9], allow_trait_values = db_row[10],
                   required_for_dataset_state = db_row[11], values_are_feature_labels=db_row[12],
                   values_are_genotype_labels=db_row[13], values_are_numeric=db_row[14])

    @classmethod
    def objectify_with_tag(cls, tag: str) -> PostgreSQLAttribute:
        db_row = PostgreSQLAttribute.__get_db_select_row(tag = tag)

        return cls(parent_attribute = PostgreSQLAttribute.objectify_with_id(db_row[1]) if db_row[1] else None,
                   tag = db_row[2], text = db_row[3], priority = db_row[4], db_id = db_row[0],
                   allow_as_filter = db_row[5], allow_for_dataset = db_row[6], allow_for_genotype = db_row[7],
                   allow_for_performance = db_row[8], allow_for_sample = db_row[9], allow_trait_values = db_row[10],
                   required_for_dataset_state = db_row[11], values_are_feature_labels = db_row[12],
                   values_are_genotype_labels = db_row[13], values_are_numeric = db_row[14])

    def write_to_db(self, db_cur_session: psycopg2.cursor | None = None):
        self.__db_insert(db_cur_session=db_cur_session) if self._id is None else self.__db_update(db_cur_session=db_cur_session)

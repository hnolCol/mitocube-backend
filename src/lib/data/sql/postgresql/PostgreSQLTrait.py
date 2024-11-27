from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Tuple, List, Self

import re
import psycopg2

import lib.data as dlib
import lib.data.sql.postgresql as psql

class PostgreSQLTrait(dlib.ABCTrait):

    @abstractmethod
    def add_to_dataset_id(self, dataset_id: int) -> dlib.ABCTraitNode:
        pass

    @abstractmethod
    def add_to_sample_id(self, sample_id: int) -> dlib.ABCTraitNode:
        pass

    @staticmethod
    def does_tag_exist(attribute: dlib.ABCAttribute, tag: str) -> bool:
        pass

    @staticmethod
    def get_all_traits(attributes: Dict[int, dlib.ABCAttribute] | None = None) -> Dict[id, PostgreSQLTrait]:
        pass

    @staticmethod
    def is_keyword_taken(keyword: str) -> bool:
        pass

    @classmethod
    def objectify_with_id(cls, db_id: int) -> PostgreSQLTrait:
        pass

    @classmethod
    def objectify_with_tag(cls, full_tag: str | None) -> PostgreSQLTrait:
        pass

    @classmethod
    def objectify_with_keyword(cls, keyword: str) -> PostgreSQLTrait:
        pass

    def create(self):
        pass

    def update(self):
        pass


# Old Code

class PostgreSQLTrait(dlib.ABCTrait):
    def __db_insert(self, db_cur_session: psycopg2.cursor | None = None):
        if self._id is not None:
            raise dlib.ABCAttributeError("Unable to perform database INSERT with PostgreSQLTrait that does already exist in database.")

        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("INSERT INTO traits (attribute_id, tag, text, keyword, description) VALUES (%(attribute_id)s, %(tag)s, %(text)s, %(keyword)s, %(description)s) RETURNING id;",
                           {"attribute_id": self._attribute.get_id(), "tag": self._tag, "text": self._text, "keyword": self._keyword, "description": self._description})

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

            db_cur.execute("UPDATE traits SET attribute_id = %(attribute_id)s, tag = %(tag)s, text = %(text)s, keyword = %(keyword)s, description = %(description)s WHERE id = %(db_id)s;",
                           {"db_id": self._id, "attribute_id": self._attribute_id, "tag": self._tag, "text": self._text, "keyword": self._keyword, "description": self._description})

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
        db_row = PostgreSQLTrait.__get_db_select_row(db_id = self._id, full_tag = self.get_full_tag(),
                                                     keyword = self._keyword, db_cur_session = db_cur_session)

        self._id = db_row[0]
        self._attribute = psql.PostgreSQLAttribute.objectify_with_id(db_id = db_row[1], catch_parent = True),
        self._tag = db_row[2]
        self._text = db_row[3]
        self._keyword = db_row[4]
        self._description = db_row[5]

    @staticmethod
    def __get_db_select_row(db_id: int | None = None, full_tag: str | None = None, keyword: str | None = None,
                            db_cur_session: psycopg2.cursor | None = None) -> Tuple[Any]:
        if db_id is None and full_tag is None and keyword is None:
            raise dlib.ABCAttributeError("Neither id (db_id), (full) tag nor keyword set for PostgreSQLAttribute. Unable to perform SELECT.")

        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            if db_id is not None:
                db_cur.execute("""SELECT id, attribute_id, tag, text, keyword, description FROM traits WHERE id = {db_id};""", {"db_id": db_id})
            elif full_tag is not None:
                pre_tag, post_tag = re.findall("(att_[\w]+):([\w]+)", full_tag)[0]  # Question: Any additional checks required?

                db_cur.execute("""SELECT t.id, t.attribute_id, t.tag, t.text, t.keyword, t.description 
                                    FROM traits AS t 
                                        LEFT JOIN attributes AS a ON t.attribute_id = a.id 
                                    WHERE t.tag = %(post_tag)s AND a.tag = %(pre_tag)s;""", {"post_tag": post_tag, "pre_tag": pre_tag})
            else:
                db_cur.execute("""SELECT id, attribute_id, tag, text, keyword, description FROM traits WHERE keyword = {keyword};""", {"keyword": keyword})

            if db_cur.rowcount != 1:
                raise dlib.ABCTraitNotFoundError("Provided id, tags nor keyword match a single Trait. Number of returned rows = {n}".format(n=db_cur.rownumber))

            db_row = db_cur.fetchone()
        finally:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

        return db_row

    @staticmethod
    def does_tag_exist(attribute: dlib.ABCAttribute, tag: str, db_cur_session: psycopg2.cursor | None = None) -> bool:
        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("SELECT EXISTS(SELECT 1 FROM traits WHERE attribute_id = %(id)s AND tag=%(tag)s);", {"id": attribute.get_id(), "tag": tag})
            does_exist = db_cur.fetchone()[0]

        finally:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

        return does_exist

    @staticmethod
    def get_all_traits(attributes: Dict[int, psql.PostgreSQLAttribute] | None = None,
                       db_cur_session: psycopg2.cursor | None = None) -> Dict[int, PostgreSQLTrait]:
        db_conn = None
        db_cur = db_cur_session

        if attributes is None:
            attributes = psql.PostgreSQLAttribute.get_all_attributes(db_cur_session)

        traits: Dict[int, PostgreSQLTrait] = {}

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("SELECT id, attribute_id, tag, text, keyword, description FROM traits ORDER BY id ASC;")

            db_rows = db_cur.fetchall()

            for db_row in db_rows:
                traits[db_row[0]] = PostgreSQLTrait(db_id = db_row[0], parent_attribute = attributes[db_row[1]],
                                                    tag = db_row[2], text = db_row[3], keyword = db_row[4],
                                                    description = db_row[5])

        finally:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

        # traits = Dict[str, PostgreSQLTrait] = {obj.get_tag():obj for key, obj in traits.items()}
        return traits

    @staticmethod
    def is_keyword_taken(keyword: str, db_cur_session: psycopg2.cursor | None = None) -> bool:
        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("SELECT EXISTS(SELECT 1 FROM traits WHERE keyword=%(keyword)s);", {"keyword": keyword})
            does_exist = db_cur.fetchone()[0]

        finally:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

        return does_exist

    @classmethod
    def objectify_with_id(cls, db_id: int, db_cur_session: psycopg2.cursor | None = None) -> dlib.ABCTrait:
        db_row = PostgreSQLTrait.__get_db_select_row(db_id = db_id, db_cur_session = db_cur_session)

        return cls(parent_attribute = psql.PostgreSQLAttribute.objectify_with_id(db_id = db_row[1], catch_parent = True),
                   tag = db_row[2], text = db_row[3], keyword = db_row[4], description = db_row[5], db_id = db_row[0])

    @classmethod
    def objectify_with_tag(cls, full_tag: str | None, db_cur_session: psycopg2.cursor | None = None) -> dlib.ABCTrait:
        db_row = PostgreSQLTrait.__get_db_select_row(full_tag = full_tag, db_cur_session = db_cur_session)  # ToDo: Check with tag versus full_tag

        return cls(parent_attribute = psql.PostgreSQLAttribute.objectify_with_id(db_id = db_row[1], catch_parent = True),
                   tag=db_row[2], text=db_row[3], keyword=db_row[4], description=db_row[5], db_id=db_row[0])

    @classmethod
    def objectify_with_keyword(cls, keyword: str, db_cur_session: psycopg2.cursor | None = None) -> dlib.ABCTrait:
        db_row = PostgreSQLTrait.__get_db_select_row(keyword = keyword, db_cur_session = db_cur_session)  # ToDo: Check with tag versus full_tag

        return cls(parent_attribute = psql.PostgreSQLAttribute.objectify_with_id(db_id = db_row[1], catch_parent = True),
                   tag=db_row[2], text=db_row[3], keyword=db_row[4], description=db_row[5], db_id=db_row[0])

    #@classmethod
    #def objectify_with_attribute_id(cls, db_id: int) -> Dict[str, dlib.ABCTrait]:  # ToDo: Implement?
    #    """SELECT t.id, t.attribute_id, t.tag, t.text, t.keyword, t.description, nm.trait_value, nm.trait_unit, nm.dataset_id
    #       FROM traits AS t LEFT JOIN nm_traits_datasets AS nm ON t.id = nm.trait_id WHERE t.id = {db_id};"""
    #    pass

    #@classmethod
    #def objectify_with_attribute_tag(cls, tag: str) -> Dict[str, dlib.ABCTrait]:  # ToDo: Implement?
    #    """SELECT t.id, t.attribute_id, t.tag, t.text, t.keyword, t.description, nm.trait_value, nm.trait_unit, nm.dataset_id
    #       FROM traits AS t LEFT JOIN nm_traits_datasets AS nm ON t.id = nm.trait_id WHERE t.id = {db_id};"""
    #    pass

    def write_to_db(self, db_cur_session: psycopg2.cursor | None = None):
        self.__db_insert(db_cur_session=db_cur_session) if self._id is None else self.__db_update(db_cur_session=db_cur_session)



from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Tuple, List, Self

import lib.data as dlib
import lib.data.sql.postgresql as psql


class PostgreSQLAttribute(dlib.ABCAttribute):

    def __db_insert(self):

        if self._id is not None:
            raise dlib.ABCUserError("Unable to perform database INSERT with PostgreSQLAttribute that does already exist in database.")
        elif PostgreSQLAttribute.does_tag_exist(tag = self._tag):
            raise dlib.ABCUserError("Unable to perform database INSERT. PostgreSQLAttribute, tag '{tag}' does already exist in database.".format(tag = self._tag))

        try:
            db_conn = psql.PostgreSQLConnection().getConnection()
            db_cur = db_conn.cursor()

            db_cur.execute("""INSERT INTO sec_users(parent_id, tag, text, priority, allow_as_filter, allow_for_dataset, allow_for_genotype, allow_for_performance, allow_for_sample, allow_trait_values, required_for_dataset_state) 
                                    VALUES (%(parent_id)s, %(tag)s, %(text)s, %(priority)s, %(allow_as_filter)s, 
                                    %(allow_for_dataset)s, %(allow_for_genotype)s, %(allow_for_performance)s, 
                                    %(allow_for_sample)s, %(allow_trait_values)s, %(required_for_dataset_state)s) RETURNING id;""",
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
                            "required_for_dataset_state": self._required_for_dataset_state})

            db_row = db_cur.fetchone()
            self._id = db_row[0]

            db_conn.commit()
            psql.PostgreSQLConnection().returnConnection(db_conn)
        except Exception as err:
            if "db_conn" in locals():
                db_conn.rollback()  # fixme: cleaner way of doing this?
            if "db_cur" in locals():
                psql.PostgreSQLConnection().returnConnection(db_conn)
            raise err

    def __db_select(self):  # ToDo: Update
        db_row = PostgreSQLAttribute.__get_db_select_row(db_id=self._id, tag=self._tag)

        self._id = db_row[0]
        self._parent = None  # ToDo: db_row[1]  None if db_row[2] is None else psql.PostgreSQLResearchGroup.create_from_id(db_id=db_row[2])  # ToDo: Update with final method / function
        self._tag = db_row[2]
        self._text = db_row[3]
        self._priority = db_row[4]
        self._allow_as_filter = db_row[5]
        self._allow_for_dataset = db_row[6]
        self._allow_for_genotype = db_row[7]
        self._allow_for_performance = db_row[8]
        self._allow_for_sample = db_row[9]
        self._allow_trait_values = db_row[10]
        self._required_for_dataset_state = db_row[11]  # ToDo: Check


    @staticmethod
    def __db_update(self):
        if not self.does_exist():  # ToDo: Implement
            raise dlib.ABCUserError("Unable to perform database UPDATE on PostgreAttribute that does not exist in database.")

        try:
            db_conn = psql.PostgreSQLConnection().getConnection()
            db_cur = db_conn.cursor()

            # ToDo: Change
            db_cur.execute("""UPDATE sec_users SET username = %(username)s, research_group_id = %(research_group_id)s, 
                                    firstname = %(firstname)s, lastname = %(lastname)s, email = %(email)s, 
                                    email_verified = %(email_verified)s, base64_image = %(base64_image)s, 
                                    profile_text = %(profile_text)s, orcid = %(orcid)s, url = %(url)s, 
                                    allow_login = %(allow_login)s, updated_on = NOW(), expires_after = %(expires_after)s) 
                                WHERE id = %(db_id)s RETURNING updated_on;""",
                           {"db_id": self._id, "username": self._username, "research_group_id": self._research_group.get_id(),
                            "firstname": self._firstname, "lastname": self._lastname,
                            "email": self._email, "email_verified": self._is_email_verified,
                            "base64_image": self._base64_image,
                            "profile_text": self._profile_text, "orcid": self._orcid, "url": self._url,
                            "allow_login": self._db_allow_login, "expires_after": self._expires_after
                            })

            self._updated_on = db_cur.fetchone()[0]

            db_conn.commit()
            psql.PostgreSQLConnection().returnConnection(db_conn)
        except Exception as err:
            if "db_conn" in locals():
                db_conn.rollback()  # fixme: cleaner way of doing this?
            if "db_cur" in locals():
                psql.PostgreSQLConnection().returnConnection(db_conn)
            raise err

    @staticmethod
    def __get_db_select_row(db_id: int | None = None, tag: str | None = None) -> Tuple[Any]:
        if db_id is None and tag is None:
            raise dlib.ABCAttributeError("Neither id (db_id) nor tag set for PostgreSQLAttribute. Unable to perform SELECT.")

        try:
            db_conn = psql.PostgreSQLConnection().getConnection()
            db_cur = db_conn.cursor()

            if db_id is None:
                db_cur.execute("""SELECT id, parent_id, tag, text, priority, allow_as_filter, 
                        allow_for_dataset, allow_for_genotype, allow_for_performance, allow_for_sample, allow_trait_values, required_for_dataset_state 
                    FROM attributes WHERE tag = {tag};""", {"tag": tag})
            else:
                db_cur.execute("""SELECT id, parent_id, tag, text, priority, allow_as_filter, 
                        allow_for_dataset, allow_for_genotype, allow_for_performance, allow_for_sample, allow_trait_values, required_for_dataset_state 
                    FROM attributes WHERE id = {db_id};""", {"db_id": db_id})

            if db_cur.rowcount != 1:
                raise dlib.ABCUserError("Provided id nor name does not match a single Attribute. Number of returned rows = {n}".format(n=db_cur.rownumber))

            db_row = db_cur.fetchone()

            psql.PostgreSQLConnection().returnConnection(db_conn)

            return db_row
        except Exception as err:
            if "db_cur" in locals():
                psql.PostgreSQLConnection().returnConnection(db_conn)
            raise err

    @staticmethod
    def does_tag_exist(tag: str) -> bool:
        try:
            db_conn = psql.PostgreSQLConnection().getConnection()
            db_cur = db_conn.cursor()

            db_cur.execute("SELECT EXISTS(SELECT 1 FROM attributes WHERE tag=%(tag)s);", {"tag": tag})
            does_exist = db_cur.fetchone()[0]

            psql.PostgreSQLConnection().returnConnection(db_conn)
        except Exception as err:
            if "db_cur" in locals():
                psql.PostgreSQLConnection().returnConnection(db_conn)  # fixme: cleaner way of doing this?
            raise err

        return does_exist

    @classmethod
    def objectify_with_id(cls, db_id: int, catch_parent: bool = False) -> dlib.ABCAttribute:
        db_row = PostgreSQLAttribute.__get_db_select_row(db_id = db_id)

        # Question: catch_parent = catch_parent or = False? Latter would prevent a possible circular import / endless loop
        return cls(PostgreSQLAttribute.objectify_with_id(db_row[1], catch_parent = catch_parent) if catch_parent else None,
                   tag = db_row[2], text = db_row[3], priority = db_row[4], db_id = db_row[0],
                   allow_as_filter = db_row[5], allow_for_dataset = db_row[6], allow_for_genotype = db_row[7],
                   allow_for_performance = db_row[8], allow_for_sample = db_row[9], allow_trait_values = db_row[10],
                   required_for_dataset_state = db_row[11])  # ToDo: Check

    @classmethod
    def objectify_with_tag(cls, tag: str, catch_parent: bool = False) -> dlib.ABCAttribute:
        db_row = PostgreSQLAttribute.__get_db_select_row(tag = tag)

        # Question: catch_parent = catch_parent or = False? Latter would prevent a possible circular import / endless loop
        return cls(None if catch_parent is None else PostgreSQLAttribute.objectify_with_id(db_row[1], catch_parent = catch_parent),
                   tag = db_row[2], text = db_row[3], priority = db_row[4], db_id = db_row[0],
                   allow_as_filter = db_row[5], allow_for_dataset = db_row[6], allow_for_genotype = db_row[7],
                   allow_for_performance = db_row[8], allow_for_sample = db_row[9], allow_trait_values = db_row[10],
                   required_for_dataset_state = db_row[11])  # ToDo: Check

    def write(self):
        self.__db_insert() if self._id is None else self.__db_update()

class PostgreSQLTrait(dlib.ABCTrait):

    @staticmethod
    def __get_db_select_row(db_id: int | None = None, tag: str | None = None, keyword: str | None = None) -> Tuple[Any]:
        if db_id is None and tag is None and keyword is None:
            raise dlib.ABCAttributeError("Neither id (db_id), tag nor keyword set for PostgreSQLAttribute. Unable to perform SELECT.")

        try:
            db_conn = psql.PostgreSQLConnection().getConnection()
            db_cur = db_conn.cursor()

            if db_id is not None:
                db_cur.execute("""SELECT id, attribute_id, tag, text, keyword, description FROM traits WHERE tag = {tag};""", {"tag": tag})
            elif db_id is not None:
                db_cur.execute("""SELECT id, attribute_id, tag, text, keyword, description FROM traits WHERE id = {db_id};""", {"db_id": db_id})
            else:
                db_cur.execute("""SELECT id, attribute_id, tag, text, keyword, description FROM traits WHERE id = {keyword};""", {"keyword": keyword})

            if db_cur.rowcount != 1:
                raise dlib.ABCUserError("Provided id nor name does not match a single Trait. Number of returned rows = {n}".format(n=db_cur.rownumber))

            db_row = db_cur.fetchone()

            psql.PostgreSQLConnection().returnConnection(db_conn)

            return db_row
        except Exception as err:
            if "db_cur" in locals():
                psql.PostgreSQLConnection().returnConnection(db_conn)
            raise err

    @staticmethod
    def does_tag_exist(tag: str) -> bool:
        try:
            db_conn = psql.PostgreSQLConnection().getConnection()
            db_cur = db_conn.cursor()

            db_cur.execute("SELECT EXISTS(SELECT 1 FROM traits WHERE tag=%(tag)s);", {"tag": tag})
            does_exist = db_cur.fetchone()[0]

            psql.PostgreSQLConnection().returnConnection(db_conn)
        except Exception as err:
            if "db_cur" in locals():
                psql.PostgreSQLConnection().returnConnection(db_conn)  # fixme: cleaner way of doing this?
            raise err

        return does_exist

    @staticmethod
    def is_keyword_taken(keyword: str) -> bool:
        try:
            db_conn = psql.PostgreSQLConnection().getConnection()
            db_cur = db_conn.cursor()

            db_cur.execute("SELECT EXISTS(SELECT 1 FROM traits WHERE keyword=%(keyword)s);", {"keyword": keyword})
            does_exist = db_cur.fetchone()[0]

            psql.PostgreSQLConnection().returnConnection(db_conn)
        except Exception as err:
            if "db_cur" in locals():
                psql.PostgreSQLConnection().returnConnection(db_conn)  # fixme: cleaner way of doing this?
            raise err

        return does_exist

    @classmethod
    def objectify_with_id(cls, db_id: int) -> dlib.ABCTrait:
        db_row = PostgreSQLTrait.__get_db_select_row(db_id = db_id)

        return cls(parent_attribute = None,  # ToDo: Check db_row[1],
                   tag = db_row[2], text = db_row[3], keyword = db_row[4], description = db_row[5], db_id = db_row[0])

    @classmethod
    def objectify_with_tag(cls, tag: str | None, full_tag: str | None, ) -> dlib.ABCTrait:
        db_row = PostgreSQLTrait.__get_db_select_row(tag = tag)  # ToDo: Check with tag versus full_tag

        return cls(parent_attribute=None,  # ToDo: Check db_row[1],
                   tag=db_row[2], text=db_row[3], keyword=db_row[4], description=db_row[5], db_id=db_row[0])

    @classmethod
    def objectify_with_keyword(cls, keyword: str) -> dlib.ABCTrait:
        db_row = PostgreSQLTrait.__get_db_select_row(keyword = keyword)  # ToDo: Check with tag versus full_tag

        return cls(parent_attribute=None,  # ToDo: Check db_row[1],
                   tag=db_row[2], text=db_row[3], keyword=db_row[4], description=db_row[5], db_id=db_row[0])

    @classmethod
    def objectify_with_attribute_id(cls, db_id: int) -> Dict[str, dlib.ABCTrait]:  # ToDo: Implement
        """SELECT t.id, t.attribute_id, t.tag, t.text, t.keyword, t.description, nm.trait_value, nm.trait_unit, nm.dataset_id
           FROM traits AS t LEFT JOIN nm_traits_datasets AS nm ON t.id = nm.trait_id WHERE t.id = {db_id};"""
        pass

    @classmethod
    def objectify_with_attribute_label(cls, label: str) -> Dict[str, dlib.ABCTrait]:  # ToDo: Implement
        """SELECT t.id, t.attribute_id, t.tag, t.text, t.keyword, t.description, nm.trait_value, nm.trait_unit, nm.dataset_id
           FROM traits AS t LEFT JOIN nm_traits_datasets AS nm ON t.id = nm.trait_id WHERE t.id = {db_id};"""

    @classmethod
    def objectify_with_dataset_id(cls, db_id: int) -> Dict[str, dlib.ABCTrait]:  # ToDo: Implement
        """SELECT t.id, t.attribute_id, t.tag, t.text, t.keyword, t.description, nm.trait_value, nm.trait_unit, nm.dataset_id
           FROM traits AS t LEFT JOIN nm_traits_datasets AS nm ON t.id = nm.trait_id WHERE nm.dataset_id = {db_id};"""
        pass

    @classmethod
    def objectify_with_dataset_label(cls, label: str) -> Dict[str, dlib.ABCTrait]:  # ToDo: Implement
        """SELECT t.id, t.attribute_id, t.tag, t.text, t.keyword, t.description, nm.trait_value, nm.trait_unit, nm.dataset_id
           FROM traits AS t
            LEFT JOIN nm_traits_datasets AS nm ON t.id = nm.trait_id
            LEFT JOIN datasets AS d ON nm.trait_id = d.id
            WHERE d.label = {label};"""
        pass

    def write(self):
        # self.__db_insert(use_id=False, password=None) if self._id is None else self.__db_update()
        pass
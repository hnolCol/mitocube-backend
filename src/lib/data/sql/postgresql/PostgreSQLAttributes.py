from __future__ import annotations

import re
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
            db_cur.execute("""INSERT INTO attributes(parent_id, tag, text, priority, allow_as_filter, allow_for_dataset, allow_for_genotype, allow_for_performance, allow_for_sample, allow_trait_values, required_for_dataset_state) 
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
    def __db_update(self, db_cur_session: psycopg2.cursor | None = None):
        if not self.does_exist():  # ToDo: Implement
            raise dlib.ABCAttributeError("Unable to perform database UPDATE on PostgreAttribute that does not exist in database.")

        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            # ToDo: Change
            db_cur.execute("""UPDATE attributes SET username = %(username)s, research_group_id = %(research_group_id)s, 
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
                        allow_for_dataset, allow_for_genotype, allow_for_performance, allow_for_sample, allow_trait_values, required_for_dataset_state 
                    FROM attributes WHERE tag = %(tag)s;""", {"tag": tag})
            else:
                db_cur.execute("""SELECT id, parent_id, tag, text, priority, allow_as_filter, 
                        allow_for_dataset, allow_for_genotype, allow_for_performance, allow_for_sample, allow_trait_values, required_for_dataset_state 
                    FROM attributes WHERE id = %(db_id)s;""", {"db_id": db_id})

            if db_cur.rowcount != 1:
                raise dlib.ABCAttributeError("Provided id nor name does not match a single Attribute. Number of returned rows = {n}".format(n=db_cur.rownumber))

            db_row = db_cur.fetchone()
        finally:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

        return db_row

    @staticmethod
    def get_all_attributes(db_cur_session: psycopg2.cursor | None = None) -> Dict[id, PostgreSQLAttribute]:

        db_conn = None
        db_cur = db_cur_session

        attributes: Dict[int, PostgreSQLAttribute] = {}

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("""SELECT id, parent_id, tag, text, priority, allow_as_filter, allow_for_dataset, allow_for_genotype, allow_for_performance, allow_for_sample, allow_trait_values, required_for_dataset_state FROM attributes ORDER by id ASC;""")

            db_rows = db_cur.fetchall()

            for db_row in db_rows:
                attributes[db_row[0]] = PostgreSQLAttribute(db_id=db_row[0],
                                                            parent_attribute = attributes[db_row[1]] if db_row[1] else None, # Should work since list is sorted ASC for ids!
                                                            tag=db_row[2], text=db_row[3], priority=db_row[4],
                                                            allow_as_filter=db_row[5],
                                                            allow_for_dataset=db_row[6],
                                                            allow_for_genotype=db_row[7],
                                                            allow_for_performance=db_row[8],
                                                            allow_trait_values=db_row[10],
                                                            allow_for_sample=db_row[9],
                                                            required_for_dataset_state=db_row[11])

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
    def objectify_with_id(cls, db_id: int, catch_parent: bool = False) -> PostgreSQLAttribute:
        db_row = PostgreSQLAttribute.__get_db_select_row(db_id = db_id)

        # Question: catch_parent = catch_parent or = False? Latter would prevent a possible circular import / endless loop
        return cls(PostgreSQLAttribute.objectify_with_id(db_row[1], catch_parent = catch_parent) if db_row[1] is not None and catch_parent else None,
                   tag = db_row[2], text = db_row[3], priority = db_row[4], db_id = db_row[0],
                   allow_as_filter = db_row[5], allow_for_dataset = db_row[6], allow_for_genotype = db_row[7],
                   allow_for_performance = db_row[8], allow_for_sample = db_row[9], allow_trait_values = db_row[10],
                   required_for_dataset_state = db_row[11])  # ToDo: Check

    @classmethod
    def objectify_with_tag(cls, tag: str, catch_parent: bool = False) -> PostgreSQLAttribute:
        db_row = PostgreSQLAttribute.__get_db_select_row(tag = tag)

        # Question: catch_parent = catch_parent or = False? Latter would prevent a possible circular import / endless loop
        return cls(None if catch_parent is None else PostgreSQLAttribute.objectify_with_id(db_row[1], catch_parent = catch_parent),
                   tag = db_row[2], text = db_row[3], priority = db_row[4], db_id = db_row[0],
                   allow_as_filter = db_row[5], allow_for_dataset = db_row[6], allow_for_genotype = db_row[7],
                   allow_for_performance = db_row[8], allow_for_sample = db_row[9], allow_trait_values = db_row[10],
                   required_for_dataset_state = db_row[11])  # ToDo: Check

    def read(self, db_cur_session: psycopg2.cursor | None = None):
        self.__db_select(db_cur_session=db_cur_session)

    def write(self, db_cur_session: psycopg2.cursor | None = None):
        self.__db_insert(db_cur_session=db_cur_session) if self._id is None else self.__db_update(db_cur_session=db_cur_session)

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
        self._attribute = PostgreSQLAttribute.objectify_with_id(db_id = db_row[1], catch_parent = True),
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
                raise dlib.ABCAttributeError("Provided id, tags nor keyword match a single Trait. Number of returned rows = {n}".format(n=db_cur.rownumber))

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
    def get_all_traits(attributes: Dict[int, PostgreSQLAttribute] | None = None,
                       db_cur_session: psycopg2.cursor | None = None) -> Dict[id, PostgreSQLTrait]:
        db_conn = None
        db_cur = db_cur_session

        if attributes is None:
            attributes = PostgreSQLAttribute.get_all_attributes(db_cur_session)

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
    def objectify_with_id(cls, db_id: int) -> dlib.ABCTrait:
        db_row = PostgreSQLTrait.__get_db_select_row(db_id = db_id)

        return cls(parent_attribute = PostgreSQLAttribute.objectify_with_id(db_id = db_row[1], catch_parent = True),
                   tag = db_row[2], text = db_row[3], keyword = db_row[4], description = db_row[5], db_id = db_row[0])

    @classmethod
    def objectify_with_tag(cls, full_tag: str | None) -> dlib.ABCTrait:
        db_row = PostgreSQLTrait.__get_db_select_row(full_tag = full_tag)  # ToDo: Check with tag versus full_tag

        return cls(parent_attribute = PostgreSQLAttribute.objectify_with_id(db_id = db_row[1], catch_parent = True),
                   tag=db_row[2], text=db_row[3], keyword=db_row[4], description=db_row[5], db_id=db_row[0])

    @classmethod
    def objectify_with_keyword(cls, keyword: str) -> dlib.ABCTrait:
        db_row = PostgreSQLTrait.__get_db_select_row(keyword = keyword)  # ToDo: Check with tag versus full_tag

        return cls(parent_attribute = PostgreSQLAttribute.objectify_with_id(db_id = db_row[1], catch_parent = True),
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

    def read(self, db_cur_session: psycopg2.cursor | None = None):
        self.__db_select(db_cur_session=db_cur_session)

    def write(self, db_cur_session: psycopg2.cursor | None = None):
        self.__db_insert(db_cur_session=db_cur_session) if self._id is None else self.__db_update(db_cur_session=db_cur_session)


class PostgreSQLTraitValue(dlib.ABCTraitValue):
    @staticmethod
    def __get_db_select_row(dataset_id: int | None = None, dataset_label: str | None = None,
                            sample_id: int | None = None, sample_label: str | None = None,
                            db_cur_session: psycopg2.cursor | None = None) -> List[Tuple[Any]]:
        if dataset_id is None and dataset_label is None and sample_id is None and sample_label is None:
            raise dlib.ABCAttributeError("Require at least the id or label of a dataset or sample to select respective Trait values. Unable to perform SELECT.")

        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            if dataset_id and sample_label is None:
                db_cur.execute("""SELECT t.id, t.attribute_id, t.tag, t.text, t.keyword, t.description, nm.trait_value, nm.trait_unit, nm.dataset_id 
                    FROM traits AS t 
                        LEFT JOIN nm_traits_datasets AS nm ON t.id = nm.trait_id 
                    WHERE nm.dataset_id = %(db_id)s;""",
                               {"db_id": dataset_id})
            elif dataset_label:
                db_cur.execute("""SELECT t.id, t.attribute_id, t.tag, t.text, t.keyword, t.description, nm.trait_value, nm.trait_unit, nm.dataset_id
                    FROM traits AS t
                        LEFT JOIN nm_traits_datasets AS nm ON t.id = nm.trait_id
                        LEFT JOIN datasets AS d ON nm.dataset_id = d.id
                    WHERE d.label = %(label)s;""",
                               {"label": dataset_label})
            elif sample_id:
                db_cur.execute("""SELECT t.id, t.attribute_id, t.tag, t.text, t.keyword, t.description, nm.trait_value, nm.trait_unit, nm.sample_id
                    FROM traits AS t LEFT JOIN nm_traits_samples AS nm ON t.id = nm.trait_id WHERE nm.sample_id = %(db_id)s;""",
                               {"db_id": sample_id})
            elif sample_label and dataset_id:
                db_cur.execute("""SELECT t.id, t.attribute_id, t.tag, t.text, t.keyword, t.description, nm.trait_value, nm.trait_unit, nm.sample_id
                    FROM traits AS t
                        LEFT JOIN nm_traits_samples AS nm ON t.id = nm.trait_id
                        LEFT JOIN samples AS s ON nm.sample_id = s.id
                    WHERE s.dataset_id = %(dataset_id)s AND s.label = %(label)s;""",
                               {"dataset_id": dataset_id, "label": sample_label})
            else:  # Should not be reachable
                raise dlib.ABCAttributeError("Require at least the id or label of a dataset or sample to select respective Trait values. Unable to perform SELECT.")

            if db_cur.rowcount < 1:
                raise dlib.ABCAttributeError("Provided id or labels did not match a single Trait. Number of returned rows = {n}".format(n=db_cur.rownumber))

            db_rows = db_cur.fetchall()

        finally:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

        return db_rows

    def add_to_dataset_id(self, dataset_id: int, db_cur_session: psycopg2.cursor | None = None):
        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("INSERT INTO nm_traits_datasets (trait_id, trait_value, trait_unit, dataset_id) VALUES (%(trait_id)s, %(trait_value)s, %(trait_unit)s, %(dataset_id)s);",
                           {"trait_id": self._trait.get_id(),
                            "trait_value": self._value,
                            "trait_unit": self._unit,
                            "dataset_id": dataset_id})
            db_conn.commit()

        finally:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

    def add_to_sample_id(self, sample_id: int, db_cur_session: psycopg2.cursor | None = None):
        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("INSERT INTO nm_traits_samples (trait_id, trait_value, trait_unit, sample_id) VALUES (%(trait_id)s, %(trait_value)s, %(trait_unit)s, %(sample_id)s);",
                           {"trait_id": self._trait.get_id(),
                            "trait_value": self._value,
                            "trait_unit": self._unit,
                            "sample_id": sample_id})
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

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("DELETE FROM nm_traits_datasets WHERE trait_id=%(trait_id)s AND dataset_id=%(dataset_id)s;",
                           {"trait_id": self._trait.get_id(),
                            "dataset_id": dataset_id})
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

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("DELETE FROM nm_traits_samples WHERE trait_id=%(trait_id)s AND sample_id=%(sample_id)s;",
                           {"trait_id": self._trait.get_id(),
                            "sample_id": sample_id})
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
    def objectify_with_dataset_id(cls, db_id: int) -> List[PostgreSQLTraitValue]:
        db_rows = PostgreSQLTraitValue.__get_db_select_row(dataset_id = db_id)

        trait_values: List[PostgreSQLTraitValue] = []

        for db_row in db_rows:
            trait_values.append(cls(trait = PostgreSQLTrait(parent_attribute = PostgreSQLAttribute.objectify_with_id(db_id = db_row[1],
                                                                                                                     catch_parent= True),
                                                            tag = db_row[2], text = db_row[3], keyword = db_row[4],
                                                            description = db_row[5], db_id = db_row[0]),
                                    value = db_row[6], unit = db_row[7]))

        return trait_values

    @classmethod
    def objectify_with_dataset_label(cls, label: str) -> List[PostgreSQLTraitValue]:
        db_rows = PostgreSQLTraitValue.__get_db_select_row(dataset_label = label)

        trait_values: List[PostgreSQLTraitValue] = []

        for db_row in db_rows:
            trait_values.append(cls(trait = PostgreSQLTrait(parent_attribute = PostgreSQLAttribute.objectify_with_id(db_id = db_row[1],
                                                                                                                     catch_parent= True),
                                                            tag = db_row[2], text = db_row[3], keyword = db_row[4],
                                                            description = db_row[5], db_id = db_row[0]),
                                    value = db_row[6], unit = db_row[7]))

        return trait_values

    @classmethod
    def objectify_with_sample_id(cls, sample_id: int) -> List[PostgreSQLTraitValue]:
        db_rows = PostgreSQLTraitValue.__get_db_select_row(sample_id = sample_id)

        trait_values: List[PostgreSQLTraitValue] = []

        for db_row in db_rows:
            trait_values.append(cls(trait = PostgreSQLTrait(parent_attribute = PostgreSQLAttribute.objectify_with_id(db_id = db_row[1],
                                                                                                                     catch_parent= True),
                                                            tag = db_row[2], text = db_row[3], keyword = db_row[4],
                                                            description = db_row[5], db_id = db_row[0]),
                                    value = db_row[6], unit = db_row[7]))

        return trait_values

    @classmethod
    def objectify_with_sample_label(cls, dataset_id: int, label: str) -> List[PostgreSQLTraitValue]:
        db_rows = PostgreSQLTraitValue.__get_db_select_row(dataset_id = dataset_id, sample_label = label)

        trait_values: List[PostgreSQLTraitValue] = []

        for db_row in db_rows:
            trait_values.append(cls(trait = PostgreSQLTrait(parent_attribute = PostgreSQLAttribute.objectify_with_id(db_id = db_row[1],
                                                                                                                     catch_parent= True),
                                                            tag = db_row[2], text = db_row[3], keyword = db_row[4],
                                                            description = db_row[5], db_id = db_row[0]),
                                    value = db_row[6], unit = db_row[7]))

        return trait_values

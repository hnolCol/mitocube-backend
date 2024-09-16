from __future__ import annotations

from typing import Any, List, Tuple

import psycopg2

import lib.data as dlib
import lib.data.sql.postgresql as psql


class PostgreSQLResearchGroup(dlib.ABCResearchGroup):

    def __get_db_select_row(db_id: int | None = None, db_cur_session: psycopg2.cursor | None = None) -> Tuple[Any]:
        if db_id is None:
            raise dlib.ABCResearchGroupError("No id (db_id) set for PostgreSQLResearchGroup. Unable to perform SELECT.")

        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("""SELECT research_group, research_group_short, institute, base64_image, profile_text, 
                                    contact_address, contact_email, url 
                                FROM sec_research_groups WHERE id = %(db_id)s;""", {"db_id": db_id})

            db_row = db_cur.fetchone()
        finally:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

        return db_row

    def __db_insert(self, use_id: bool = False, db_cur_session: psycopg2.cursor | None = None):
        if self.does_exist():
            raise dlib.ABCResearchGroupError("Unable to perform database INSERT with PostgreSQLResearchGroup that does already exist in database.")

        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            if use_id:
                if self._id is None:
                    raise dlib.ABCResearchGroupError("No id (db_id) set for ABCResearchGroup. Unable to perform INSERT with assigned id.")

                db_cur.execute("""INSERT INTO sec_research_groups(id, research_group, research_group_short, institute, base64_image, profile_text, contact_address, contact_email, url) 
                                    VALUES (%(db_id)s, %(research_group)s, %(research_group_short)s, %(institute)s, %(base64_image)s, %(profile_text)s, %(contact_address)s, %(contact_email)s, %(url)s);""",
                               {"db_id": self._id,
                                "research_group": self._name,
                                "research_group_short": self._name_short,
                                "institute": self._institute,
                                "base64_image": self._base64_image,
                                "profile_text": self._profile_text,
                                "contact_address": self._contact_address,
                                "contact_email": self._contact_email,
                                "url": self._url
                                })
            else:
                db_cur.execute("""INSERT INTO sec_research_groups(research_group, research_group_short, institute, base64_image, profile_text, contact_address, contact_email, url) 
                                    VALUES (%(db_id)s, %(research_group)s, %(research_group_short)s, %(institute)s, %(base64_image)s, %(profile_text)s, %(contact_address)s, %(contact_email)s, %(url)s) RETURNING id;""",
                               {"research_group": self._name,
                                "research_group_short": self._name_short,
                                "institute": self._institute,
                                "base64_image": self._base64_image,
                                "profile_text": self._profile_text,
                                "contact_address": self._contact_address,
                                "contact_email": self._contact_email,
                                "url": self._url
                                })

                self._id = db_cur.fetchone()[0]

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
        db_row = PostgreSQLResearchGroup.__get_db_select_row(self._id, db_cur_session = db_cur_session)

        self._name = db_row[0]
        self._name_short = db_row[1]
        self._institute = db_row[2]
        self._base64_image = db_row[3]
        self._profile_text = db_row[4]
        self._contact_address = db_row[5]
        self._contact_email = db_row[6]
        self._url = db_row[7]

    def __db_update(self, db_cur_session: psycopg2.cursor | None = None):
        if not self.does_exist():
            raise dlib.ABCResearchGroupError("Unable to perform database UPDATE on PostgreSQLResearchGroup that does not exist in database.")

        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("""UPDATE sec_research_groups SET research_group = %(research_group)s, research_group_short = %(research_group_short)s, 
                                    institute = %(institute)s, base64_image = %(base64_image)s, profile_text = %(profile_text)s, 
                                    contact_address = %(contact_address)s, contact_email = %(contact_email)s, url = %(url)s
                                WHERE id = %(db_id)s;""",
                           {"db_id": self._id,
                            "research_group": self._name,
                            "research_group_short": self._name_short,
                            "institute": self._institute,
                            "base64_image": self._base64_image,
                            "profile_text": self._profile_text,
                            "contact_address": self._contact_address,
                            "contact_email": self._contact_email,
                            "url": self._url
                            })

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
    def objectify_from_id(cls, db_id: int) -> PostgreSQLResearchGroup:
        db_row = PostgreSQLResearchGroup.__get_db_select_row(self._id)

        return cls(name = db_row[0], name_short = db_row[1], institute = db_row[2], base64_image = db_row[3],
                   profile_text = db_row[4], contact_address = db_row[5], contact_email = db_row[6], url = db_row[7],
                   db_id = db_id)

    @classmethod
    def objectify_from_object(cls, rgroup: dlib.ABCResearchGroup) -> PostgreSQLResearchGroup:
        return cls(name = rgroup._name, name_short = rgroup._name_short, institute = rgroup._institute,
                   base64_image = rgroup._base64_image,  # Question: Do we need a deep copy of the object here?
                   profile_text = rgroup._profile_text,
                   contact_address = rgroup._contact_address, contact_email = rgroup._contact_email,
                   url = rgroup._url, db_id = rgroup._id)

    def does_exist(self, db_cur_session: psycopg2.cursor | None = None):
        if self._id is None:
            return False
        else:
            return PostgreSQLResearchGroup.does_exist_with_id(self._id, db_cur_session = db_cur_session)

    @staticmethod
    def does_exist_with_id(db_id: int, db_cur_session: psycopg2.cursor | None = None) -> bool:
        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("SELECT EXISTS(SELECT 1 FROM sec_research_groups WHERE id=%(id)s", {"id": db_id})
            does_exist = db_cur.fetchone()[0]

        finally:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

        return does_exist

    def read(self, db_cur_session: psycopg2.cursor | None = None):
        self.__db_select(db_cur_session = db_cur_session)

    def write(self, db_cur_session: psycopg2.cursor | None = None):
        self.__db_insert(use_id=False, db_cur_session = db_cur_session) if self._id is None else self.__db_update(db_cur_session=db_cur_session)

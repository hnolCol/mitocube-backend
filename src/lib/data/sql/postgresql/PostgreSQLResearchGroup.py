from __future__ import annotations

import lib.data as dlib
import lib.data.sql.postgresql as psql


class PostgreSQLResearchGroup(dlib.ABCResearchGroup):

    # def __init__(self, db_id: int, title: str, description: str | None, datasets: List[dlib.ABCDataset] | None = None):
    def __init__(self, **kwargs):  # FixMe: Would love multiple constructors... what is the clean python alternative?
        super().__init__(**kwargs)
        # super().__init__(db_id=-1, title="str", description:="str", datasets=None)

    # @staticmethod

    def __db_insert(self, use_id: bool = False):
        if self.does_exist():
            raise dlib.ABCResearchGroupError("Unable to perform database INSERT with PostgreSQLResearchGroup that does already exist in database.")

        try:
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
            raise dlib.ABCResearchGroupError("No id (db_id) set for PostgreSQLResearchGroup. Unable to perform SELECT.")

        try:
            db_conn = psql.PostgreSQLConnection().getConnection()
            db_cur = db_conn.cursor()

            db_cur.execute("""SELECT research_group, research_group_short, institute, base64_image, profile_text, 
                                    contact_address, contact_email, url 
                                FROM sec_research_groups WHERE id = %(db_id)s;""", {"db_id": self._id})

            db_row = db_cur.fetchone()
            self._name = db_row[0]
            self._name_short = db_row[1]
            self._institute = db_row[2]
            self._base64_image = db_row[3]
            self._profile_text = db_row[4]
            self._contact_address = db_row[5]
            self._contact_email = db_row[6]
            self._url = db_row[7]

            psql.PostgreSQLConnection().returnConnection(db_conn)
        except Exception as err:
            if "db_cur" in locals():
                psql.PostgreSQLConnection().returnConnection(db_conn)
            raise err

    def __db_update(self):
        if not self.does_exist():
            raise dlib.ABCResearchGroupError("Unable to perform database UPDATE on PostgreSQLResearchGroup that does not exist in database.")

        try:
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

            db_conn.commit()
            psql.PostgreSQLConnection().returnConnection(db_conn)
        except Exception as err:
            if "db_conn" in locals():
                db_conn.rollback()  # Fixme: cleaner way of doing this?
            if "db_cur" in locals():
                psql.PostgreSQLConnection().returnConnection(db_conn)
            raise err

    @classmethod
    def create_from_id(cls, db_id: int) -> PostgreSQLResearchGroup:  # ToDo: inherit it from the parent class, is it possible to overwrite return type? any restrictions form parent class?
        obj = cls(db_id = db_id)  # Fixme: This will cause an exception since not all argument are served
        obj.read()

        return obj

    def does_exist(self):
        if self._id is None:
            return False
        else:
            return PostgreSQLResearchGroup.does_exist_with_id(self._id)

    @staticmethod
    def does_exist_with_id(db_id: int) -> bool:
        try:
            db_conn = psql.PostgreSQLConnection().getConnection()
            db_cur = db_conn.cursor()

            db_cur.execute("SELECT EXISTS(SELECT 1 FROM sec_research_groups WHERE id=%(id)s", {"id": db_id})
            does_exist = db_cur.fetchone()[0]

            psql.PostgreSQLConnection().returnConnection(db_conn)
        except Exception as err:
            if "db_cur" in locals():
                psql.PostgreSQLConnection().returnConnection(db_conn)  # fixme: cleaner way of doing this?
            raise err

        return does_exist

    def read(self):
        self.__db_select()

    def write(self):
        self.__db_insert(use_id=False) if self._id is None else self.__db_update()

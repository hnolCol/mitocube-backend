from __future__ import annotations

from typing import Any, Dict, List, Tuple

import psycopg2

import lib.data as dlib
import lib.data.sql.postgresql as psql


class PostgreSQLUser(dlib.ABCUser):

    def __db_insert(self, use_id: bool = False, password: str | None = None, db_cur_session: psycopg2.cursor | None = None):

        if self.does_exist():
            raise dlib.ABCUserError("Unable to perform database INSERT with PostgreSQLUser that does already exist in database.")
        elif PostgreSQLUser.is_username_taken(self._username):
            raise dlib.ABCUserError("Unable to perform database INSERT. PostgreSQLUser with that username does already exist in database.")

        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            if use_id:
                if self._id is None:
                    raise dlib.ABCUserError("No id (db_id) set for PostgreSQLUser. Unable to perform INSERT with assigned id.")

                db_cur.execute("""INSERT INTO sec_users(id, username, research_group_id, firstname, lastname, email, 
                                        email_verified, base64_image, profile_text, orcid, url, allow_login, 
                                        password, personal_salt, created_on, updated_on, last_login_on, expires_after) 
                                    VALUES (%(db_id)s, %(username)s, %(research_group_id)s, %(firstname)s, %(lastname)s, %(email)s, 
                                        %(email_verified)s, %(base64_image)s, %(profile_text)s, %(orcid)s, %(url)s, %(allow_login)s, 
                                        crypt(%(password)s, gen_salt('bf', 8)),  %(personal_salt)s, 
                                        NOW(), -- created_on
                                        NOW(), -- updated_on
                                        NULL, -- last_login_on
                                        %(expires_after)s) RETURNING created_on, updated_on, last_login_on;""",
                               {"db_id": self._id, "username": self._username,
                                "research_group_id": self._research_group.get_id(),
                                "firstname": self._firstname, "lastname": self._lastname,
                                "email": self._email, "email_verified": self._is_email_verified,
                                "base64_image": self._base64_image,
                                "profile_text": self._profile_text, "orcid": self._orcid, "url": self._url,
                                "allow_login": self._db_allow_login,
                                "password": password if password else "kj34_Ga25!7S8nÖzt$gHrd",  # Todo: Implement get_random_string(128),
                                "personal_salt": self._personal_salt, "expires_after": self._expires_after
                                })

                db_row = db_cur.fetchone()
                self._created_on = db_row[0]
                self._updated_on = db_row[1]
                self._last_login_on = db_row[2]
            else:
                db_cur.execute("""INSERT INTO sec_users(username, research_group_id, firstname, lastname, email, 
                                        email_verified, base64_image, profile_text, orcid, url, allow_login, 
                                        password, personal_salt, created_on, updated_on, last_login_on, expires_after) 
                                    VALUES (%(username)s, %(research_group_id)s, %(firstname)s, %(lastname)s, %(email)s, 
                                        %(email_verified)s, %(base64_image)s, %(profile_text)s, %(orcid)s, %(url)s, %(allow_login)s, 
                                        crypt(%(password)s, gen_salt('bf', 8)),  %(personal_salt)s,  
                                        NOW(), -- created_on
                                        NOW(), -- updated_on
                                        NULL, -- last_login_on
                                        %(expires_after)s) RETURNING id, created_on, updated_on, last_login_on;""",
                               {"username": self._username,
                                "research_group_id": None if self._research_group is None else self._research_group.get_id(),
                                "firstname": self._firstname, "lastname": self._lastname,
                                "email": self._email, "email_verified": self._is_email_verified,
                                "base64_image": self._base64_image,
                                "profile_text": self._profile_text, "orcid": self._orcid, "url": self._url,
                                "allow_login": self._db_allow_login,
                                "password": password if password else "kj34_Ga25!7S8nÖzt$gHrd",  # Todo: Implement get_random_string(128),
                                "personal_salt": self._personal_salt, "expires_after": self._expires_after
                                })

                db_row = db_cur.fetchone()
                self._id = db_row[0]
                self._created_on = db_row[1]
                self._updated_on = db_row[2]
                self._last_login_on = db_row[3]

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
    def __get_db_select_row(db_id: int | None = None,
                            email: str | None = None,
                            username: str | None = None,
                            db_cur_session: psycopg2.cursor | None = None) -> Tuple[Any]:
        if db_id is None and username is None and email is None:
            raise dlib.ABCUserError("Neither id (db_id), email nor username set for selection of PostgreSQLUser. Unable to perform SELECT.")

        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            if db_id is not None:
                db_cur.execute("""SELECT id, username, research_group_id, firstname, lastname, email, email_verified, base64_image, profile_text, orcid, url, allow_login, personal_salt, created_on, updated_on, last_login_on, expires_after
                                    FROM sec_users WHERE id = %(db_id)s;""", {"db_id": db_id})
            elif email is not None:
                db_cur.execute("""SELECT id, username, research_group_id, firstname, lastname, email, email_verified, base64_image, profile_text, orcid, url, allow_login, personal_salt, created_on, updated_on, last_login_on, expires_after
                                    FROM sec_users WHERE email = %(email)s;""", {"email": email})
            elif username is not None:
                db_cur.execute("""SELECT id, username, research_group_id, firstname, lastname, email, email_verified, base64_image, profile_text, orcid, url, allow_login, personal_salt, created_on, updated_on, last_login_on, expires_after
                                    FROM sec_users WHERE username = %(username)s;""", {"username": username})

            if db_cur.rowcount != 1:
                raise dlib.ABCUserNotFoundError("Provided user id or name does not match a single user. Number of returned rows = {n}".format(n=db_cur.rownumber))

            db_row = db_cur.fetchone()
        finally:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

        return db_row

    def __db_select(self, db_cur_session: psycopg2.cursor | None = None):
        db_row = PostgreSQLUser.__get_db_select_row(db_id=self._id, username=self._username, db_cur_session = db_cur_session)

        self._id = db_row[0]
        self._username = db_row[1]
        self._research_group = None if db_row[2] is None else psql.PostgreSQLResearchGroup.objectify_with_id(db_id=db_row[2], db_cur_session=db_cur_session)
        self._firstname = db_row[3]
        self._lastname = db_row[4]
        self._email = db_row[5]
        self._is_email_verified = db_row[6]
        self._base64_image = db_row[7]
        self._profile_text = db_row[8]
        self._orcid = db_row[9]
        self._url = db_row[10]
        self._db_allow_login = db_row[11]
        self._personal_salt = db_row[12]
        self._created_on = db_row[13]
        self._updated_on = db_row[14]
        self._last_login_on = db_row[15]
        self._expires_after = db_row[16]

    def __db_update(self, db_cur_session: psycopg2.cursor | None = None):
        if not self.does_exist():
            raise dlib.ABCUserError("Unable to perform database UPDATE on PostgreSQLUser that does not exist in database.")

        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("""UPDATE sec_users SET username = %(username)s, research_group_id = %(research_group_id)s, 
                                    firstname = %(firstname)s, lastname = %(lastname)s, email = %(email)s, 
                                    email_verified = %(email_verified)s, base64_image = %(base64_image)s, 
                                    profile_text = %(profile_text)s, orcid = %(orcid)s, url = %(url)s, 
                                    allow_login = %(allow_login)s, updated_on = NOW(), expires_after = %(expires_after)s 
                                WHERE id = %(db_id)s RETURNING updated_on;""",
                           {"db_id": self._id,
                            "username": self._username,
                            "research_group_id": self._research_group.get_id() if self._research_group else None,
                            "firstname": self._firstname,
                            "lastname": self._lastname,
                            "email": self._email,
                            "email_verified": self._is_email_verified,
                            "base64_image": self._base64_image,
                            "profile_text": self._profile_text,
                            "orcid": self._orcid,
                            "url": self._url,
                            "allow_login": self._db_allow_login,
                            "expires_after": self._expires_after.strftime("%Y-%m-%d %H:%M:%S")
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

    def __db_update_password(self, password: str, db_cur_session: psycopg2.cursor | None = None):
        if not self.does_exist():
            raise dlib.ABCUserError("Unable to perform database UPDATE on PostgreSQLUser that does not exist in database.")

        encoded_password = password  # ToDo: Change password encoding from SQL-DB (current) to passlib.context CryptContext

        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("UPDATE sec_users SET password=crypt(%(password)s, gen_salt('bf', 8)), updated_on = NOW() WHERE id=%(id)s RETURNING updated_on;",
                           {"id": self._id, "password": encoded_password})

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

    def _test_password(self, password: str, db_cur_session: psycopg2.cursor | None = None) -> bool:  # ToDo: change password test to crypt (?) python package, see older code
        if self._id is None and self._username is None:
            raise dlib.ABCUserError("Neither id (db_id) nor username set for PostgreSQLUser. Unable to perform password check.")

        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            if self._id is None:
                db_cur.execute("""SELECT (password = crypt(%(password)s, password)) FROM sec_users WHERE username = %(username)s;""",
                               {"username": self._username, "password": password})
            else:
                db_cur.execute("""SELECT (password = crypt(%(password)s, password)) FROM sec_users WHERE id = %(db_id)s;""",
                               {"db_id": self._id, "password": password})

            db_row = db_cur.fetchone()
            is_password_valid = db_row[0]

        finally:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

        return is_password_valid

    def _write_last_login_date(self, db_cur_session: psycopg2.cursor | None = None):
        if not self.does_exist():
            raise dlib.ABCUserError("Unable to perform database UPDATE on PostgreSQLUser that does not exist in database.")

        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("UPDATE sec_users SET last_login_on = %(last_login_on)s WHERE id = %(db_id)s;",
                           {"db_id": self._id,
                            "last_login_on": self._last_login_on.strftime("%Y-%m-%d %H:%M:%S")
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

    def does_exist(self, db_cur_session: psycopg2.cursor | None = None) -> bool:
        if self._id is None:
            return False
        else:
            return PostgreSQLUser.does_exist_with_id(self._id,db_cur_session = db_cur_session)

    @staticmethod
    def does_exist_with_id(db_id: int, db_cur_session: psycopg2.cursor | None = None) -> bool:
        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("SELECT EXISTS(SELECT 1 FROM sec_users WHERE id=%(id)s);", {"id": db_id})
            does_exist = db_cur.fetchone()[0]

        finally:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

        return does_exist

    @staticmethod
    def does_exist_with_username(username: str, db_cur_session: psycopg2.cursor | None = None) -> bool:
        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("SELECT EXISTS(SELECT 1 FROM sec_users WHERE username=%(username)s);", {"username": username})
            does_exist = db_cur.fetchone()[0]

        finally:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

        return does_exist

    @staticmethod
    def get_users(usernames: List[str] = None, db_cur_session: psycopg2.cursor | None = None) -> Dict[str, PostgreSQLUser]:
        users = {}

        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            if usernames is None:
                pass  # ToDo: Forgot to finish. return all or list of selected
            db_cur.execute("SELECT id, username, research_group_id, firstname, lastname, email, email_verified, base64_image, profile_text, orcid, url, allow_login, personal_salt, created_on, updated_on, last_login_on, expires_after FROM sec_users;")
            db_rows = db_cur.fetchall()

            for db_row in db_rows:
                user = PostgreSQLUser(db_id = db_row[0], username = db_row[1],
                                      research_group = None if db_row[2] is None else psql.PostgreSQLResearchGroup.objectify_with_id(db_id=db_row[2], db_cur_session = db_cur_session),
                                      firstname = db_row[3], lastname = db_row[4], email = db_row[5],
                                      base64_image = db_row[7], profile_text = db_row[8], orcid = db_row[9],
                                      url = db_row[10], allow_login = db_row[11], expires_after = db_row[16])

                user._is_email_verified = db_row[6]
                user._personal_salt = db_row[12]
                user._created_on = db_row[13]
                user._updated_on = db_row[14]
                user._last_login_on = db_row[15]

                users[user._username] = user

        finally:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

        return users

    @staticmethod
    def get_user_names(db_cur_session: psycopg2.cursor | None = None) -> Dict[str, int]:
        usernames = {}

        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("SELECT id, username FROM sec_users;")
            db_rows = db_cur.fetchall()

            for db_row in db_rows:
                usernames[db_row[1]] = db_row[0]

        finally:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

        return usernames

    @staticmethod
    def is_username_taken(username: str, db_cur_session: psycopg2.cursor | None = None) -> bool:
        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("SELECT EXISTS(SELECT 1 FROM sec_users WHERE username=%(user)s);", {"user": username})
            does_exist = db_cur.fetchone()[0]

        finally:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

        return does_exist

    @classmethod
    def objectify_with_id(cls, db_id: int, db_cur_session: psycopg2.cursor | None = None) -> PostgreSQLUser:
        db_row = PostgreSQLUser.__get_db_select_row(db_id = db_id, db_cur_session = db_cur_session)

        user = PostgreSQLUser(db_id = db_row[0], username = db_row[1], firstname = db_row[3], lastname = db_row[4], email = db_row[5],
                              research_group = None if db_row[2] is None else psql.PostgreSQLResearchGroup.objectify_with_id(db_id = db_row[2], db_cur_session = db_cur_session),
                              base64_image = db_row[7], profile_text = db_row[8], orcid = db_row[9], url = db_row[10],
                              allow_login = db_row[11], expires_after = db_row[16])

        user._is_email_verified = db_row[6]
        user._personal_salt = db_row[12]
        user._created_on = db_row[13]
        user._updated_on = db_row[14]
        user._last_login_on = db_row[15]
        user._expires_after = db_row[16]

        return user

    @classmethod
    def objectify_with_username(cls, username: str, db_cur_session: psycopg2.cursor | None = None) -> PostgreSQLUser:
        db_row = PostgreSQLUser.__get_db_select_row(username = username, db_cur_session = db_cur_session)

        user = PostgreSQLUser(db_id = db_row[0], username = db_row[1], firstname = db_row[3], lastname = db_row[4], email = db_row[5],
                              research_group = None if db_row[2] is None else psql.PostgreSQLResearchGroup.objectify_with_id(db_id = db_row[2], db_cur_session = db_cur_session),
                              base64_image = db_row[7], profile_text = db_row[8], orcid = db_row[9], url = db_row[10],
                              allow_login = db_row[11], expires_after = db_row[16])

        user._is_email_verified = db_row[6]
        user._personal_salt = db_row[12]
        user._created_on = db_row[13]
        user._updated_on = db_row[14]
        user._last_login_on = db_row[15]
        user._expires_after = db_row[16]

        return user

    @classmethod
    def objectify_with_email(cls, email: str, db_cur_session: psycopg2.cursor | None = None) -> PostgreSQLUser:
        db_row = PostgreSQLUser.__get_db_select_row(email = email, db_cur_session = db_cur_session)

        user = PostgreSQLUser(db_id = db_row[0], username = db_row[1], firstname = db_row[3], lastname = db_row[4], email = db_row[5],
                              research_group = None if db_row[2] is None else psql.PostgreSQLResearchGroup.objectify_with_id(db_id=db_row[2], db_cur_session = db_cur_session),
                              base64_image = db_row[7], profile_text = db_row[8], orcid = db_row[9], url = db_row[10],
                              allow_login = db_row[11], expires_after = db_row[16])

        user._is_email_verified = db_row[6]
        user._personal_salt = db_row[12]
        user._created_on = db_row[13]
        user._updated_on = db_row[14]
        user._last_login_on = db_row[15]
        user._expires_after = db_row[16]

        return user

    @classmethod
    def objectify_with_object(cls, user: dlib.ABCUser) -> PostgreSQLUser:
        user = PostgreSQLUser(db_id = None, username = user._username, firstname = user._firstname,
                              lastname = user._lastname, email = user._email,
                              research_group = user._research_group,  # Question: Copy would be cleaner here. No default function? import copy.deepcopy(xyz)?
                              base64_image = user._base64_image,  # Question: Deepcopy here?
                              profile_text = user._profile_text,  orcid = user._orcid,  url = user._url,
                              allow_login = user._db_allow_login, expires_after = user._expires_after)

        user._is_email_verified = user._is_email_verified
        user._personal_salt = user._personal_salt
        user._created_on = user._created_on  # Question: Deepcopy here?
        user._updated_on = user._updated_on  # Question: Deepcopy here?
        user._last_login_on = user._last_login_on  # Question: Deepcopy here?
        user._expires_after = user._expires_after  # Question: Deepcopy here?

        return user

    # ToDo: Implement methods to update  salts
    def write_to_db(self, db_cur_session: psycopg2.cursor | None = None):
        self.__db_insert(use_id=False, password=None, db_cur_session = db_cur_session) if self._id is None else self.__db_update(db_cur_session = db_cur_session)

    def write_password(self, password: str, db_cur_session: psycopg2.cursor | None = None):
        self.__db_update_password(password = password, db_cur_session = db_cur_session)

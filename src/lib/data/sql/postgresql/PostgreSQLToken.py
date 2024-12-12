from __future__ import annotations

from abc import abstractmethod
from typing import Any, Dict, Tuple, Self
from datetime import datetime, timedelta
import string
import random
import hashlib

import psycopg2

import lib.data as dlib
import lib.data.sql.postgresql as psql


class PostgreSQLToken(dlib.ABCToken):

    @staticmethod
    def _add_token(token: dlib.ABCToken, db_cur_session: psycopg2.cursor | None = None):
        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

                db_cur.execute("""INSERT INTO sec_tokens(md5_token, token_type, username, agent, ip, value, expires_after) 
                                    VALUES(%(md5_token)s, %(token_type)s, %(username)s, %(agent)s, %(ip)s, %(value)s, %(expires_after)s);""",
                               {"md5_token": token.get_md5_token(),
                                "token_type": str(token.get_token_type()),
                                "username": token.get_username(),
                                "agent": token.get_agent(),
                                "ip": token.get_ip(),
                                "value": token.get_value(),
                                "expires_after": token.get_expires_after()})

            if db_conn:
                db_conn.commit()
        except Exception as err:  # fixme: switch to psycopg 3 to be able to use with statements? https://github.com/psycopg/psycopg2/pull/367 https://www.psycopg.org/psycopg3/docs/advanced/pool.html#connection-pools
            if db_conn:
                db_conn.rollback()
            raise err
        finally:
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

    @staticmethod
    def clear_expired_tokens(db_cur_session: psycopg2.cursor | None = None):
        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

                # WITH deleted AS (DELETE FROM sec_tokens WHERE expires_after < NOW() RETURNING *) SELECT count(*) FROM deleted;
                db_cur.execute("DELETE FROM sec_tokens WHERE expires_after < NOW();")

            if db_conn:
                db_conn.commit()
        except Exception as err:  # fixme: switch to psycopg 3 to be able to use with statements? https://github.com/psycopg/psycopg2/pull/367 https://www.psycopg.org/psycopg3/docs/advanced/pool.html#connection-pools
            if db_conn:
                db_conn.rollback()
            raise err
        finally:
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

    @classmethod
    def objectify_token(cls, token: str, token_type: dlib.ABCTokenType, db_cur_session: psycopg2.cursor | None = None) -> PostgreSQLToken:
        db_conn = None
        db_cur = db_cur_session
        db_row: Tuple[Any] = tuple()
        md5_token = cls.token_to_md5(token = token)

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("""SELECT username, agent, ip, value, expires_after 
                                FROM sec_tokens 
                                WHERE md5_token = %(md5_token)s AND token_type = %(token_type)s;""",
                           {"md5_token": md5_token, "token_type": str(token_type)})

            if db_cur.rowcount != 1:
                raise dlib.TokenNotFoundError("Provided information does not match a single genotype.")
            db_row = db_cur.fetchone()
        except Exception as err:  # fixme: switch to psycopg 3 to be able to use with statements? https://github.com/psycopg/psycopg2/pull/367 https://www.psycopg.org/psycopg3/docs/advanced/pool.html#connection-pools
            if db_conn:
                db_conn.rollback()
            raise err
        finally:
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

        return PostgreSQLToken(token = None, md5_token = md5_token, token_type = token_type,
                               username = db_row[0],
                               agent = db_row[1],
                               ip = db_row[2],
                               value = db_row[3],
                               expires_after = db_row[4])

    @classmethod
    def remove_token(cls, token: dlib.ABCToken, db_cur_session: psycopg2.cursor | None = None):
        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

                db_cur.execute("DELETE FROM sec_tokens WHERE md5_token = %(md5_token)s AND token_type = %(token_type)s;",
                               {"md5_token": token.get_md5_token(), "token_type": str(token.get_token_type())})

            if db_conn:
                db_conn.commit()
        except Exception as err:  # fixme: switch to psycopg 3 to be able to use with statements? https://github.com/psycopg/psycopg2/pull/367 https://www.psycopg.org/psycopg3/docs/advanced/pool.html#connection-pools
            if db_conn:
                db_conn.rollback()
            raise err
        finally:
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

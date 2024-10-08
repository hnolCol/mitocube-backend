from __future__ import annotations

from typing import Any, Dict, Tuple, List

import psycopg2

import lib.data as dlib
import lib.data.sql.postgresql as psql

from config import get_system_settings





# DB_SETTINGS = get_db_settings()  # Setup proper config

class PostgreSQLDatabase(dlib.ABCDatabase):  # ToDo: Move some functions to a DatabaseStat Class to keep it clean?
    """PostgreSQL implementation of the ABCDatabase class."""

    @staticmethod
    def get_n_submissions(db_cur_session: psycopg2.cursor | None = None) -> int:  # Move definition to ABCDatabase
        # ToDo: Implement BufferClass with ExpiringValue
        db_conn = None
        db_cur = db_cur_session

        n: int = -1

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("SELECT COUNT(*) AS n FROM datasets;")

            n = db_cur.fetchone()[0]

        finally:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

        """SELECT COUNT(*) AS n FROM sec_users WHERE allow_login AND expires_after > NOW();"""
        return n

    @staticmethod
    def get_n_active_datasets(db_cur_session: psycopg2.cursor | None = None) -> int:  # Move definition to ABCDatabase
        # ToDo: Implement BufferClass with ExpiringValue

        db_conn = None
        db_cur = db_cur_session

        n: int = -1

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("SELECT COUNT(*) AS n FROM datasets WHERE state > %s;", dlib.DatasetState)

            n = db_cur.fetchone()[0]

        finally:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

        """SELECT COUNT(*) AS n FROM sec_users WHERE allow_login AND expires_after > NOW();"""
        return n

    @staticmethod
    def get_n_pg_features(db_cur_session: psycopg2.cursor | None = None) -> int:  # Move definition to ABCDatabase
        # ToDo: Implement BufferClass with ExpiringValue
        db_conn = None
        db_cur = db_cur_session

        n: int = -1

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("SELECT COUNT(*) AS n FROM feature_pgs;")

            n = db_cur.fetchone()[0]

        finally:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

        """SELECT COUNT(*) AS n FROM sec_users WHERE allow_login AND expires_after > NOW();"""
        return n
        return 42

    @staticmethod
    def get_n_genotypes(db_cur_session: psycopg2.cursor | None = None) -> int:  # Move definition to ABCDatabase
        # ToDo: Implement BufferClass with ExpiringValue
        return 42

    @staticmethod
    def get_n_active_users(db_cur_session: psycopg2.cursor | None = None) -> int:  # Move definition to ABCDatabase
        # ToDo: Implement BufferClass with ExpiringValue
        db_conn = None
        db_cur = db_cur_session

        n: int = -1

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("SELECT COUNT(*) AS n FROM sec_users WHERE allow_login AND expires_after > NOW();")

            n = db_cur.fetchone()[0]

        finally:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

        """SELECT COUNT(*) AS n FROM sec_users WHERE allow_login AND expires_after > NOW();"""
        return n





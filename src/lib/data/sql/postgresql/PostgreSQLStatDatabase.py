from __future__ import annotations

from typing import Any, Dict, Tuple, List

import psycopg2

import lib.data as dlib
import lib.data.sql.postgresql as psql

from config import get_system_settings

# DB_SETTINGS = get_db_settings()  # Setup proper config


# class PostgreSQLStatDatabase(dlib.CachedStatDatabase):  # ToDo: do it differently, maybe with decorator
class PostgreSQLStatDatabase(dlib.ABCStatDatabase):
    @staticmethod
    def _determine_n_submissions(db_cur_session: psycopg2.cursor | None = None) -> int:  # Move definition to ABCDatabase
        db_conn = None
        db_cur = db_cur_session

        n: int
        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("SELECT COUNT(*) AS n FROM datasets;")

            n = db_cur.fetchone()[0]

        finally:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

        return n

    @staticmethod
    def _determine_n_active_datasets(db_cur_session: psycopg2.cursor | None = None) -> int:  # Move definition to ABCDatabase
        db_conn = None
        db_cur = db_cur_session

        n: int

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("SELECT COUNT(*) AS n FROM datasets WHERE state > %(state)s;", {"state": dlib.DatasetState.ACTIVE})

            n = db_cur.fetchone()[0]

        finally:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

        return n

    @staticmethod
    def _determine_n_pg_features(db_cur_session: psycopg2.cursor | None = None) -> int:  # Move definition to ABCDatabase
        db_conn = None
        db_cur = db_cur_session

        n: int

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("SELECT COUNT(*) AS n FROM feature_pgs;")

            n = db_cur.fetchone()[0]

        finally:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

        return n

    @staticmethod
    def _determine_n_genotypes(db_cur_session: psycopg2.cursor | None = None) -> int:  # Move definition to ABCDatabase
        # ToDo: Implement
        return 42

    @staticmethod
    def _determine_n_active_users(db_cur_session: psycopg2.cursor | None = None) -> int:  # Move definition to ABCDatabase
        db_conn = None
        db_cur = db_cur_session

        n: int

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("SELECT COUNT(*) AS n FROM sec_users WHERE allow_login AND expires_after > NOW();")

            n = db_cur.fetchone()[0]

        finally:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

        return n

    @staticmethod
    def get_n_submissions() -> int:
        return PostgreSQLStatDatabase._determine_n_submissions()

    @staticmethod
    def get_n_active_datasets() -> int:
        return PostgreSQLStatDatabase._determine_n_active_datasets()

    @staticmethod
    def get_n_pg_features() -> int:
        return PostgreSQLStatDatabase._determine_n_pg_features()

    @staticmethod
    def get_n_genotypes() -> int:
        return PostgreSQLStatDatabase._determine_n_genotypes()

    @staticmethod
    def get_n_active_users() -> int:
        return PostgreSQLStatDatabase._determine_n_active_users()

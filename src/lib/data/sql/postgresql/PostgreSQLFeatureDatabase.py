from __future__ import annotations

from abc import abstractmethod
from typing import List
from threading import Lock
import os

import pandas
import pandas as pd
import numpy as np

import psycopg2

from config import get_system_settings
from lib.designpatterns import SingletonABCMeta
import lib.data as dlib
from lib.data.panda import PandaFeatureDatabase
import lib.data.sql.postgresql as psql

class PostgreSQLFeatureDatabase(PandaFeatureDatabase):
    # Columns: ['index', 'key', 'entry', 'proteins', 'genes', 'organism', 'organism_id', 'aa_length', 'mass', 'proteom_id', 'sql_id', 'is_grouped']
    # Index (Columns): ix_proteom_id ix_organism_id ix_key ix_entry ix_sql_id

    def __init__(self):
        super().__init__()

    # ToDo: Save Feature permanently in the sql database? with or without annotations?
    def _sync_db(self, db_cur_session: psycopg2.cursor | None = None):
        self._sync_db_insert_features_without_sqlid(db_cur_session = db_cur_session)
        self._sync_add_db_features_missing(db_cur_session = db_cur_session)

    def _sync_add_db_features_missing(self, db_cur_session: psycopg2.cursor | None = None):
        # ToDo: Implement, select all db features and those that are not listed yet
        pass

    def _sync_db_insert_features_without_sqlid(self, db_cur_session: psycopg2.cursor | None = None):
        if "sql_id" in self._cached_features.columns:
            tbl_no_sql_id = self._cached_features[self._cached_features["sql_id"].isna()]

            db_conn = None
            db_cur = db_cur_session

            try:
                if db_cur is None:
                    db_conn = psql.PostgreSQLConnection().getConnection()
                    db_cur = db_conn.cursor()

                for index, row in tbl_no_sql_id.iterrows():
                    db_cur.execute("""INSERT INTO feature_pgs(label, proteome_id, is_grouped) 
                                            VALUES (%(label)s, %(proteome_id)s, %(is_grouped)s);""",
                                   {"label": row["key"], "proteome_id": row["proteom_id"], "is_grouped": ";" in row["key"]})

                if db_conn:
                    db_conn.commit()
            except Exception as err:  # fixme: switch to psycopg 3 to be able to use with statements?
                if db_conn:
                    db_conn.rollback()
                raise err
            finally:
                if db_conn:
                    psql.PostgreSQLConnection().returnConnection(db_conn)

    def _split_and_add_protein_groups(self):
        # ToDo: Implement _split_and_add_protein_groups(self)
        print(" > PostgreSQLFeatureDatabase.py - _split_and_add_protein_groups(...) - TODO: Implement _split_and_add_protein_groups(self)")

    # ToDo: existing_features = dbfeature.get_not_stored_features(unique_features)
    # ToDo: missing_features = dbfeature.get_stored_features(unique_features)
    # ToDo: dbfeature.add_feature(feature, value, value values ...)


    def add_feature(self,
                    key: str, entry: str, proteins: str, genes: str,
                    organism: str, organism_id: int, proteom_id: str,
                    aa_length: int, mass: float, db_cur_session: psycopg2.cursor | None = None):

        # Fixme: This feature is added to the database, but the item will not be in the saved annotated file!
        # Consequently information entry, proteins, genes, organism, organism_id, aa_length and mass are not permanently stord

        if (proteom_id, organism_id, key, entry) in self._cached_features.index:
            raise dlib.ABCFeatureDatabaseError("A feature with the key/index ({}, {}, {}, {})) already exists. Unable to add feature to database.".format(proteom_id, organism_id, key, entry))

        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("""INSERT INTO feature_pgs(label, proteome_id, is_grouped) 
                                     VALUES (%(label)s, %(proteome_id)s, %(is_grouped)s) RETURNING ud;""",
                           {"label": key, "proteome_id": proteom_id, "is_grouped": ";" in key})

            sql_id = db_cur.fetchone()[0]

            if db_conn:
                db_conn.commit()
        except Exception as err:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                db_conn.rollback()
            raise err
        finally:
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

        # Columns: ['key', 'entry', 'proteins', 'genes', 'organism', 'organism_id', 'aa_length', 'mass', 'proteom_id', 'sql_id', 'is_grouped']
        # Index (Columns): ix_proteom_id ix_organism_id ix_key ix_entry ix_sql_id

        self._cached_features.loc[(proteom_id, int(organism_id), key, entry, int(sql_id)), :] = (key, entry, proteins, genes, int(organism), organism_id, int(aa_length), mass, proteom_id, int(sql_id), ";" in key)

    def identify_stored_feature_keys(self, features_to_test: List[str]) -> List[str]:
        identified_features = []
        existing_features = self._cached_features["key"].to_list()

        for feature in features_to_test:
            if feature in existing_features:
                identified_features.append(feature)

        return identified_features

    def identify_not_stored_feature_keys(self, features_to_test: List[str]) -> List[str]:
        missing_features = []
        existing_features = self._cached_features["key"].to_list()

        for feature in features_to_test:
            if feature not in existing_features:
                missing_features.append(feature)

        return missing_features

    def search_features(self, search_term: str) -> pd.DataFrame:
        search_list = search_term.split(sep = " ")

        if len(search_list) < 2:
            bool_list = self._cached_features["key"].str.contains('|'.join(search_list), na=False, case=False).to_list()
            ix_key = [ix for ix, value in enumerate(bool_list) if value]

            bool_list = self._cached_features["entry"].str.contains('|'.join(search_list), na=False, case=False)
            ix_entry = [ix for ix, value in enumerate(bool_list) if value]
        else:
            ix_key = []
            ix_entry = []

        bool_list = self._cached_features["genes"].str.contains('|'.join(search_list), na=False, case=False)
        ix_genes = [ix for ix, value in enumerate(bool_list) if value]

        bool_list = self._cached_features["proteins"].str.contains('|'.join(search_list), na=False, case=False)
        ix_proteins = [ix for ix, value in enumerate(bool_list) if value]

        ixs_merged = ix_key

        for ix, value in enumerate(ix_entry + ix_genes + ix_proteins):
            if value not in ixs_merged:
                ixs_merged.append(value)

        return self._cached_features.iloc[ixs_merged]

    def query_feature(self,
                      proteom_id: str | None = None,
                      organism_id: int | None = None,
                      feature: str | None = None,
                      entry: str | None = None,
                      db_id: int | None = None) -> pd.DataFrame | None:  # Question, would be a dictionary easier? What is with multiple rows?

        ixs = ("ix_proteom_id", "ix_organism_id", "ix_key", "ix_entry", "ix_sql_id")
        values = (proteom_id, organism_id, feature, entry, db_id)

        ixs_select = [ix for ix, value in enumerate(values) if value is not None]

        if len(ixs_select) < 1:
            return None
        else:
            try:
                return self._cached_features.xs(key=tuple(values[ix] for ix in ixs_select),
                                                level=tuple(ixs[ix] for ix in ixs_select),
                                                drop_level=False)
            except KeyError as e:
                print("KeyError @ PostgreSQLFeatureDatabase.get_information(...) {}".format(str(e)))  # ToDo: Log
                return None


    def read(self, db_cur_session: psycopg2.cursor | None = None):
        super().read()

        print(" > PostgreSQL read(...)")

        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("SELECT id, label, proteome_id, is_grouped FROM feature_pgs WHERE NOT is_grouped;")

            sql_tbl = pd.DataFrame(db_cur.fetchall(), columns=["sql_id",  # db_row[0]  # db_row = db_cur.fetchone()
                                                               "sql_label",  # db_row[1]
                                                               "sql_proteome_id",  # db_row[2]
                                                               "is_grouped"])  # db_row[3]

            sql_tbl.set_index(["sql_proteome_id", "sql_label"], drop=True, inplace=True)

            if sql_tbl.shape[0] < 1:
                self._cached_features["sql_id"] = np.nan
            else:
                # self._cached_features["proteom_id"] = self._cached_features.index
                self._cached_features = self._cached_features.merge(sql_tbl, how="left", left_on="ix_key", right_on="sql_label")

                # ToDo: Cleaner solution for below? issue with multiindex with merge (does not preserve indices), hence keep a copy column and restore if needed
                self._cached_features["ix_proteom_id"] = self._cached_features["proteom_id"]
                self._cached_features["ix_organism_id"] = self._cached_features["organism_id"]
                self._cached_features["ix_key"] = self._cached_features["key"]
                self._cached_features["ix_entry"] = self._cached_features["entry"]
                self._cached_features["ix_sql_id"] = self._cached_features["sql_id"]

                self._cached_features.reset_index(inplace=True)
                self._cached_features.set_index(["ix_proteom_id", "ix_organism_id", "ix_key", "ix_entry", "ix_sql_id"], drop=True, inplace=True)

                tbl_no_sql_id = self._cached_features[self._cached_features["sql_id"].isna()]

                self._sync_db(db_cur_session = db_cur_session)

                if tbl_no_sql_id.shape[0] > 0:
                    raise dlib.ABCFeatureDatabaseError(f"Not all features can be linked to a postgresql entry!")

        finally:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

    def reset(self):
        super().reset()

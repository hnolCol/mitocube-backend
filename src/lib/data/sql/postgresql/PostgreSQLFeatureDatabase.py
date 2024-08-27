from __future__ import annotations

from abc import abstractmethod
from typing import List
from threading import Lock
import os
import pandas as pd
import numpy as np

from config import get_system_settings
from lib.designpatterns import SingletonABCMeta
import lib.data as dlib
from lib.data.panda import PandaFeatureDatabase
import lib.data.sql.postgresql as psql

class PostgreSQLFeatureDatabase(PandaFeatureDatabase):
    def __init__(self):
        super().__init__()

    def _sync_db_with_cached(self):
        if "sql_id" in self._cached_features.columns:
            tbl_no_sql_id = self._cached_features[self._cached_features["sql_id"].isna()]

            try:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

                for index, row in tbl_no_sql_id.iterrows():
                    db_cur.execute("""INSERT INTO feature_pgs(label, proteome_id, is_grouped) 
                                            VALUES (%(label)s, %(proteome_id)s, %(is_grouped)s);""",
                                   {"label": row["key"], "proteome_id": row["proteom_id"], "is_grouped": ";" in row["key"]})

                db_conn.commit()
                psql.PostgreSQLConnection().returnConnection(db_conn)
            except Exception as err:
                if "db_conn" in locals():
                    db_conn.rollback()  # fixme: cleaner way of doing this?
                if "db_cur" in locals():
                    psql.PostgreSQLConnection().returnConnection(db_conn)
                raise err

    def _split_and_add_protein_groups(self):
        # TODO: Implement _split_and_add_protein_groups(self)
        print(" > PostgreSQLFeatureDatabase.py - _split_and_add_protein_groups(...) - TODO: Implement _split_and_add_protein_groups(self)" )

    def read(self):
        super().read()

        print(" > PostgreSQL read(...)")

        try:
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

                self._sync_db_with_cached()

                if tbl_no_sql_id.shape[0] > 0:
                    raise dlib.ABCFeatureDatabaseError(f"Not all features can be linked to a postgresql entry!")

            psql.PostgreSQLConnection().returnConnection(db_conn)
        except Exception as err:
            if "db_cur" in locals():
                psql.PostgreSQLConnection().returnConnection(db_conn)
            raise err

    def reset(self):
        super().reset()

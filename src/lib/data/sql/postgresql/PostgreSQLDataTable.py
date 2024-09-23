from __future__ import annotations

from typing import Any, Dict, Tuple
import pandas as pd

import psycopg2

import lib.data as dlib
import lib.data.sql.postgresql as psql

class PostgreSQLDataTable(dlib.ABCDataTable):

    @staticmethod
    def __db_select_db_row(dataset_id: int | None = None, dataset_label: str | None = None, db_cur_session: psycopg2.cursor | None = None) -> Tuple[Any]:
        if dataset_id is None and dataset_label is None:
            raise dlib.ABCDatasetError("No dataset id nor label is set for PostgreSQLDataTable. Unable to perform SELECT.")

        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            if dataset_id:
                db_cur.execute("""SELECT s.dataset_id, s.id AS sample_id, s.label AS sample, 
                    v.feature_id, 
                    f.label AS accession, f.is_grouped, f.proteome_id, 
                    b.batch_label, r.replicate_label, 
                    v.feature_value AS intensity 
                FROM samples AS s 
                    LEFT JOIN sample_replicates AS r ON s.id = r.sample_id 
                    LEFT JOIN sample_batches AS b ON s.id = b.sample_id 
                    LEFT JOIN feature_pg_values AS v ON s.id = v.sample_id 
                    LEFT JOIN feature_pgs AS f ON v.feature_id = f.id 
                WHERE s.dataset_id = %(dataset_id)s;""",  # ToDo: or v.dataset_id = <xyz> ToDo: Check if this is faster
                               {"dataset_id": dataset_id})
            else:
                db_cur.execute("""SELECT s.dataset_id, s.id AS sample_id, s.label AS sample, 
                    v.feature_id, 
                    f.label AS accession, f.is_grouped, f.proteome_id, 
                    b.batch_label, r.replicate_label, 
                    v.feature_value AS intensity 
                FROM samples AS s 
                    LEFT JOIN sample_replicates AS r ON s.id = r.sample_id 
                    LEFT JOIN sample_batches AS b ON s.id = b.sample_id 
                    LEFT JOIN feature_pg_values AS v ON s.id = v.sample_id 
                    LEFT JOIN feature_pgs AS f ON v.feature_id = f.id 
                    LEFT JOIN datasets AS d ON s.id = d.id 
                WHERE d.label = %(dataset_label)s;""",  # ToDo: or v.dataset_id = <xyz> ToDo: Check if this is faster
                               {"dataset_label": dataset_label})

            db_rows = db_cur.fetchall()

        finally:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

        return db_rows

    def __db_insert(self, db_cur_session: psycopg2.cursor | None = None):
        if self._parent_dataset and self._parent_dataset.get_internal_id():
            db_conn = None
            db_cur = db_cur_session

            try:
                if db_cur is None:
                    db_conn = psql.PostgreSQLConnection().getConnection()
                    db_cur = db_conn.cursor()

                dataset_id = self._parent_dataset.get_internal_id()

                unique_features = self.get_unique_data_features()

                fdb = psql.PostgreSQLFeatureDatabase()
                # fdb.search_features("bcl2 bax sting")
                # fdb.identify_stored_feature_keys(features_to_test=unique_features)
                features_to_remove = fdb.identify_not_stored_feature_keys(features_to_test=unique_features)

                print("The following {} features will be removed from the dataset with the id #{} "
                      "({}) due to lacking match in feature database: {}".format(len(features_to_remove),
                                                                                 dataset_id,
                                                                                 self._parent_dataset.get_external_id(),
                                                                                 str(features_to_remove)))

                # Question: How to handle missing features here? Currently they just are not added to the database.
                for feature in features_to_remove:
                    if self._data_wide is not None:
                        self._data_wide.drop(index=feature, inplace=True)

                    if self._data_long is not None:
                        self._data_long.drop(self._data_long.loc[self._data_long[self._row_index_name] == feature].index, inplace=True)

                tbl = self.get_long_table()  # We need a long table
                # 3 Columns, Example below
                # Key: A0JP43
                # sample: 20221129_DuMi_0214_VSTFFlpDMyDG_001_WT_9389
                # intensity: 22.416995

                # Stores the sample label with the internal database id
                dbids_samples: Dict[str, int] = {}  # self._data_columns  # Question: change to dict to save index?

                # Insert samples into database and saves database id into samples
                for sample in self._data_columns:
                    db_cur.execute("""INSERT INTO samples(dataset_id, label) VALUES(%(dataset_id)s, %(label)s) RETURNING id, label;""",
                                   {"dataset_id": dataset_id, "label": sample})
                    db_row = db_cur.fetchone()

                    dbids_samples[db_row[1]] = db_row[0]

                # Query features' sql database ids
                unique_features = self.get_unique_data_features()
                dbids_features: Dict[str, int] = {}
                for item in unique_features:
                    dbids_features[item] = int(fdb.query_feature(feature=item).iloc[0]["sql_id"])

                # Insert values into the database
                # Question: transformation. Currently assuming no transformation, should it be saved? user input required! Bigger issue
                sql_values = []
                for ix, row in tbl.iterrows():  # Fixme, too slow!
                    sql_values.append((dataset_id,
                                       dbids_samples[row["sample"]],
                                       dbids_features[row[self._row_index_name]],
                                       row["intensity"]))
                # Sends individual inserts to db manager. It might be faster to create one huge SQL statement, but this way is safer, currently.
                db_cur.executemany("INSERT INTO feature_pg_values(dataset_id, sample_id, feature_id, feature_value) VALUES(%s, %s, %s, %s);", sql_values)

                # Add attributes assigned to individual samples to the database
                if self._attributes_samples:
                    for sample, traits in self._attributes_samples.items():
                        for trait in traits:
                            trait.add_to_sample_id(sample_id=dbids_samples[sample], db_cur_session=db_cur)

                if db_conn:
                    db_conn.commit()
            except Exception as err:  # fixme: switch to psycopg 3 to be able to use with statements?
                if db_conn:
                    db_conn.rollback()
                raise err
            finally:
                if db_conn:
                    psql.PostgreSQLConnection().returnConnection(db_conn)
        else:
            raise dlib.ABCDataTableError("Writing the PostgreSQLDataTable is not possible without stored parent dataset.")

    def __db_select(self, db_cur_session: psycopg2.cursor | None = None):

        if self.get_parent_dataset():
            db_rows = PostgreSQLDataTable.__db_select_db_row(dataset_id = self.get_parent_dataset().get_internal_id(),
                                                             db_cur_session = db_cur_session)
        else:
            raise dlib.ABCDataTableError("Unable to perform select without set parent dataset to receive dataset id.")

        # self._data_columns: list[str] | None = None
        # self._data_long: pd.DataFrame | None = None
        # self._data_wide: pd.DataFrame | None = None
        # self._attributes_samples: dict[str, List[dlib.ABCTraitValue]] | None = attributes_samples  # sample names as keys

        print(db_rows)

        tbl = pd.DataFrame(db_rows, columns=["dataset_id",  # db_row[0]  # db_row = db_cur.fetchone()
                                             "sample_id",  # db_row[1]"sample",  # db_row[2]
                                             "feature_id",  # db_row[3]
                                             self._row_index_name,  # "accession",  # db_row[4]
                                             "is_grouped",  # db_row[5]
                                             "proteome_id",  # db_row[6]
                                             "intensity"])  # db_row[7]
        print(tbl)


    def __db_update(self, db_cur_session: psycopg2.cursor | None = None):  # Question: Do we allow updates?
        if self._parent_dataset and self._parent_dataset.get_internal_id():
            # values have no id but are unique through their foreign keys
            # DELETE FROM table_name WHERE condition;
            # Todo: implement low priority
            # Todo: track how often it happens for reminder
            raise dlib.ABCDataTableError("UPDATE not implemented")  # ToDo: Implement __db_update(...)
        else:
            raise dlib.ABCDataTableError("Writing the PostgreSQLDataTable is not possible without stored parent dataset.")

    @staticmethod
    def get_n_values_with_dataset_id(dataset_id: int, db_cur_session: psycopg2.cursor | None = None) -> int:
        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("SELECT dataset_id, COUNT(*) FROM feature_pg_values WHERE dataset_id = %(dataset_id)s GROUP BY dataset_id;",
                           {"dataset_id": dataset_id})

            if db_cur.rowcount < 1:
                n = 0
            else:
                n = db_cur.fetchone()[1]

        finally:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

        return n

    @staticmethod
    def get_n_samples_with_dataset_id(dataset_id: int, db_cur_session: psycopg2.cursor | None = None) -> int:
        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            db_cur.execute("SELECT dataset_id, COUNT(*) FROM samples WHERE dataset_id = %(dataset_id)s GROUP BY dataset_id;",
                           {"dataset_id": dataset_id})

            if db_cur.rowcount < 1:
                n = 0
            else:
                n = db_cur.fetchone()[1]

        finally:  # fixme: switch to psycopg 3 to be able to use with statements?
            if db_conn:
                psql.PostgreSQLConnection().returnConnection(db_conn)

        return n

    @classmethod
    def objectify_with_dataset_id(cls, dataset_id: int, db_cur_session: psycopg2.cursor | None = None) -> PostgreSQLDataTable:
        pass

    @classmethod
    def objectify_with_datatable(cls, datatable: dlib.ABCDataTable, db_cur_session: psycopg2.cursor | None = None) -> PostgreSQLDataTable:
        obj = PostgreSQLDataTable(parent_dataset = datatable._parent_dataset,
                                  attributes_samples = datatable._attributes_samples)  # ToDo: Latter needs to be changed to postgresql attributes if needed
        obj._data_columns = datatable._data_columns
        obj._data_long = datatable._data_long
        obj._data_wide = datatable._data_wide

        # obj._parent_dataset = datatable._parent_dataset  # ToDo: cast datatype and checks?
        # obj._attributes_samples = datatable._attributes_samples  # dict[str, List[dlib.ABCTraitValue]]

        return obj

    @classmethod
    def objectify_with_dataset_label(cls, dataset_label: str, db_cur_session: psycopg2.cursor | None = None) -> PostgreSQLDataTable:
        pass

    def read(self, db_cur_session: psycopg2.cursor | None = None):
        self.__db_select(db_cur_session = db_cur_session)

    def write(self, db_cur_session: psycopg2.cursor | None = None):
        if self.is_stored():
            raise dlib.ABCDatasetError("Unable to update / write already uploaded dataset.")
        else:
            self.__db_insert(db_cur_session=db_cur_session)




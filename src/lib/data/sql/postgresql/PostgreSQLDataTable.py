from __future__ import annotations

from typing import Any, Dict, List, Tuple
import pandas as pd

import psycopg2

import lib.data as dlib
import lib.data.sql.postgresql as psql

class PostgreSQLDataTable(dlib.ABCDataTable):

    @staticmethod
    def _db_select_db_row(dataset_id: int | None = None, dataset_label: str | None = None, db_cur_session: psycopg2.cursor | None = None) -> List[Tuple[Any]]:
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
                FROM samples AS s  ---- (SELECT * FROM samples WHERE dataset_id = %(dataset_id)s) AS s  ---- ToDo: Rearrange order
                    LEFT JOIN sample_replicates AS r ON s.id = r.sample_id 
                    LEFT JOIN sample_batches AS b ON s.id = b.sample_id 
                    LEFT JOIN feature_pg_values AS v ON s.id = v.sample_id  ---- (SELECT * FROM feature_pg_values WHERE dataset_id = %(dataset_id)s) AS v
                    LEFT JOIN feature_pgs AS f ON v.feature_id = f.id 
                WHERE v.dataset_id = %(dataset_id)s;""",  # ToDo: or s.dataset_id = <xyz> ? v.dataset_id should be faster, maybe with sub-select first
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
                WHERE d.label = %(dataset_label)s;""",
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
                db_ids_samples: Dict[str, int] = {}  # self._data_columns  # Question: change to dict to save index?

                # Insert samples into database and saves database id into samples
                for sample in self._data_columns:
                    db_cur.execute("""INSERT INTO samples(dataset_id, label) VALUES(%(dataset_id)s, %(label)s) RETURNING id, label;""",
                                   {"dataset_id": dataset_id, "label": sample})
                    db_row = db_cur.fetchone()

                    db_ids_samples[db_row[1]] = db_row[0]

                # Query features' sql database ids
                unique_features = self.get_unique_data_features()
                db_ids_features: Dict[str, int] = {}
                for item in unique_features:
                    db_ids_features[item] = int(fdb.query_feature(feature=item).iloc[0]["sql_id"])

                # Insert values into the database
                # Question: transformation. Currently assuming no transformation, should it be saved? user input required! Bigger issue
                sql_values = []
                for ix, row in tbl.iterrows():  # Fixme, too slow!
                    sql_values.append((dataset_id,
                                       db_ids_samples[row["sample"]],
                                       db_ids_features[row[self._row_index_name]],
                                       row["intensity"]))
                # Sends individual inserts to db manager. It might be faster to create one huge SQL statement, but this way is safer, currently.
                db_cur.executemany("INSERT INTO feature_pg_values(dataset_id, sample_id, feature_id, feature_value) VALUES(%s, %s, %s, %s);", sql_values)

                # Add attributes assigned to individual samples to the database
                if self._trait_values_samples:
                    for sample, traits in self._trait_values_samples.items():
                        for trait in traits:
                            trait.add_to_sample_id(sample_id=db_ids_samples[sample], db_cur_session = db_cur)  # #FixMe: should trait me more specfic here? Typing issue

                # Write Replicates to DB
                if self._replicates:
                    for sample, replicate in self._replicates.items():
                        db_cur.execute("""INSERT INTO sample_replicates (sample_id, replicate_label) VALUES (%(sample_id)s, %(replicate_label)s);""",
                                       {"sample_id": db_ids_samples[sample], "replicate_label": replicate})

                # Write Batches to DB
                if self._batches:
                    for sample, batch in self._batches.items():
                        db_cur.execute("""INSERT INTO sample_batches (sample_id, batch_label) VALUES (%(sample_id)s, %(batch_label)s);""",
                                       {"sample_id": db_ids_samples[sample], "batch_label": batch})

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

        # ToDo: Implement
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
    def _objectify_with_db_row(cls, db_rows: List[Tuple[Any]]) -> PostgreSQLDataTable | None:
        # db_rows[0]
        # 0              1                  2                         3             4                     5             6              7              8                  9
        # s.dataset_id,  s.id AS sample_id, s.label AS sample,        v.feature_id, f.label AS accession, f.is_grouped, f.proteome_id, b.batch_label, r.replicate_label, v.feature_value AS intensity
        # (152,          1481,              '20231122_BuXOSlIl6G_01', 7649,         'Q6IQ22',             False,        'UP000005640', None,          '1',               22.8541)

        if len(db_rows) < 1:
            return None
        else:
            # Create pandas long format data.frame:
            # - Key: A0JP43
            # - sample: 20221129_DuMi_0214_VSTFFlpDMyDG_001_WT_9389
            # - intensity: 22.416995
            # * f.label s.label v.feature_value --> (db_row[4], db_row[2], db_row[9])
            data_long = pd.DataFrame([(db_row[4], db_row[2], db_row[9]) for db_row in db_rows],
                                     columns = [cls._row_index_name, "sample", "intensity"])
            data_long.dropna(inplace = True)  # ToDo: Countercheck missing values, maybe introduced by the left joins

            # big_data = pd.DataFrame([(db_row[4], db_row[2], db_row[9], db_row[8], db_row[7]) for db_row in db_rows],
            #                         columns = [cls._row_index_name, "sample", "intensity", "replicate", "batch"])

            # FixMe: why are there NaN in the list?  Q9Y6Q3  20231122_BuXOSlIl6G_60        NaN

            # Break down Replicates / Batches
            # {db_row[2]: db_row[8] for db_row in db_rows if db_row[2] not in batches.keys()}
            replicates: Dict[str, str] = {}
            for db_row in db_rows:
                if db_row[2] not in replicates.keys():
                    replicates[db_row[2]] = db_row[8]

            # {db_row[2]: db_row[7] for db_row in db_rows if db_row[2] not in batches.keys()}
            batches: Dict[str, str] = {}
            for db_row in db_rows:
                if db_row[2] not in batches.keys():
                    batches[db_row[2]] = db_row[7]

            obj = cls(parent_dataset=None, data_long=data_long,
                      replicates_samples=replicates, batches_samples=batches,
                      trait_values_samples=None)

            # Receive and Set attributes for samples
            trait_values: Dict[str, List[dlib.ABCTraitValue]] | None = {}
            for sample in obj.get_data_column_names():
                # attributes[sample] =  psql.PostgreSQLTraitValue.objectify_with_sample_id(sample_id: int)  # Fixme: Would be faster
                try:  # Question: Rewrite downstream functions to not throw an exception if nothing exist and returns None?
                    trait_values[sample] = psql.PostgreSQLTraitValue.objectify_with_sample_label(dataset_id=db_rows[0][0], label=sample)
                except dlib.ABCAttributeError:
                    pass
            obj.set_samples_trait_values(trait_values_samples = trait_values)

            return obj

    @classmethod
    def objectify_with_dataset_id(cls, dataset_id: int, db_cur_session: psycopg2.cursor | None = None) -> PostgreSQLDataTable | None:
        return PostgreSQLDataTable._objectify_with_db_row(db_rows = PostgreSQLDataTable._db_select_db_row(dataset_id = dataset_id, db_cur_session = db_cur_session))

    @classmethod
    def objectify_with_dataset_label(cls, dataset_label: str, db_cur_session: psycopg2.cursor | None = None) -> PostgreSQLDataTable:
        return PostgreSQLDataTable._objectify_with_db_row(db_rows=PostgreSQLDataTable._db_select_db_row(dataset_label=dataset_label,  db_cur_session=db_cur_session))

    @classmethod
    def objectify_with_datatable(cls, datatable: dlib.ABCDataTable, db_cur_session: psycopg2.cursor | None = None) -> PostgreSQLDataTable:
        obj = PostgreSQLDataTable(parent_dataset = datatable._parent_dataset)

        obj._data_long = datatable._data_long
        obj._data_wide = datatable._data_wide

        obj._data_columns = datatable._data_columns
        obj._data_features = datatable._data_features

        obj._replicates = datatable._replicates
        obj._batches = datatable._batches
        obj._trait_values_samples = datatable._trait_values_samples  # ToDo: cast datatype and checks? (postgresql attributes) dict[str, List[dlib.ABCTraitValue]]

        obj._parent_dataset = datatable._parent_dataset  # ToDo: cast datatype and checks?

        return obj

    def read(self, db_cur_session: psycopg2.cursor | None = None):
        self.__db_select(db_cur_session = db_cur_session)

    def write(self, db_cur_session: psycopg2.cursor | None = None):
        if self.is_stored():
            raise dlib.ABCDatasetError("Unable to update / write already uploaded dataset.")
        else:
            self.__db_insert(db_cur_session=db_cur_session)

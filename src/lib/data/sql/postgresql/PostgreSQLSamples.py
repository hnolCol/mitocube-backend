from __future__ import annotations

from contextlib import suppress
from typing import Any, Dict, Tuple, List

import psycopg2

import lib.data as dlib
import lib.data.sql.postgresql as psql


class PostgreSQLSamples(dlib.ABCSamples):

    def __db_insert(self, db_cur_session: psycopg2.cursor | None = None):  # ToDo: Implement write_datatable
        if not all([sample.get_id() is None for sample in self._samples]):
            raise dlib.DatasetSampleError("Some samples do already exist in the database, unable to perform INSERT")

        db_conn = None
        db_cur = db_cur_session

        try:
            if db_cur is None:
                db_conn = psql.PostgreSQLConnection().getConnection()
                db_cur = db_conn.cursor()

            for sample in self._samples:
                db_cur.execute("INSERT INTO samples(dataset_id, label) VALUES(%(dataset_id)s, %(label)s) RETURNING id;",
                               {"dataset_id": sample.get_dataset().get_internal_id(), "label": sample.get_label()})

                sample.set_id(db_cur.fetchone()[0])

                if sample.get_batch_labels():
                    for batch in sample.get_batch_labels():
                        db_cur.execute("INSERT INTO sample_batches (sample_id, batch_label) VALUES (%(sample_id)s, %(batch_label)s);",
                                       {"sample_id": sample.get_id(), "batch_label": batch})

                if sample.get_replicate_labels():
                    for replicate in sample.get_replicate_labels():
                        db_cur.execute("INSERT INTO sample_replicates (sample_id, replicate_label) VALUES (%(sample_id)s, %(replicate_label)s);",
                                       {"sample_id": sample.get_id(), "replicate_label": replicate})

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
    def __db_select_db_rows(dataset_id: int | None = None,
                            dataset_label: str | None = None,
                            db_cur_session: psycopg2.cursor | None = None) -> Tuple[Any]:
        if dataset_id is None and dataset_label is None:
            raise dlib.ABCDatasetError("Unable to perform SELECT for Samples without dataset ids or label.")

        return ()



    def write_to_db(self):
        pass

    @staticmethod
    def objectify_by_dataset_id(dataset_id: int) -> PostgreSQLSamples:
        pass

    @staticmethod
    def objectify_by_dataset_label(label: str) -> PostgreSQLSamples:
        pass

    @staticmethod
    def objectify_by_feature(feature_label: str) -> PostgreSQLSamples:
        pass


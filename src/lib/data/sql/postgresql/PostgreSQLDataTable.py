from __future__ import annotations

import lib.data as dlib
import lib.data.sql.postgresql as psql

import pandas as pd

class PostgreSQLDataTable(dlib.ABCDataTable):

    # def __init__(self, *args):  # ToDo: Implement Smart Constructor
    #     super().__init__()
    #
    #     if len(args) != 1:
    #         raise ABCDatatableError("Only one arguments for PostgreSQLDataTable(...) is allowed. Only int for a database query or an ABCDataTable for existing data are accepted!")
    #     elif isinstance(args[0], int):
    #         # self._dataset_id = args[0]
    #         self.__db_select()
    #     elif isinstance(args[0], ABCDataset):
    #         self._dataset_id = args[0].get_internal_id()
    #         self.__db_select()
    #     elif isinstance(args[0], ABCDataTable):
    #         # self._dataset_id = None  # question: Do we need _dataset_id in super?
    #         self._load_from_tbl(args[0])
    #     else:
    #         raise ABCDatatableError("Invalid arguments for PostgreSQLDataTable(...). Only int for a database query or an ABCDataTable for existing data are accepted!")

    def __db_insert(self):
        if self._parent_dataset and self._parent_dataset.get_internal_id():
            raise dlib.ABCDatatableError("INSERT not implemented")  # ToDo: Implement __db_insert(...)
        else:
            raise dlib.ABCDatatableError("Writing the PostgreSQLDataTable is not possible without stored parent dataset.")

    def __db_select(self):
        if self._parent_dataset is None or self._parent_dataset.get_internal_id() is None:
            raise dlib.ABCDatatableError("No data does not originate from a database nor an dataset id is set.")

        try:
            db_conn = psql.PostgreSQLConnection().getConnection()
            db_cur = db_conn.cursor()

            db_cur.execute("""SELECT s.dataset_id, s.id AS sample_id, s.label AS sample, v.feature_id, f.label AS accession, f.is_grouped, f.proteome_id, v.feature_value AS intensity
                                FROM samples AS s 
                                    LEFT JOIN feature_pg_values AS v ON s.id = v.sample_id
                                    LEFT JOIN feature_pgs AS f ON v.feature_id = f.id
                                WHERE s.dataset_id = %(db_id)s;  -- v.dataset_id = <xyz> ToDo: Check if this is faster""",
                           {"db_id": self._parent_dataset.get_internal_id()})

            data_tbl = pd.DataFrame(db_cur.fetchall(), columns=["dataset_id",  # db_row[0]  # db_row = db_cur.fetchone()
                                                                "sample_id",  # db_row[1]
                                                                "sample",  # db_row[2]
                                                                "feature_id",  # db_row[3]
                                                                self._row_index_name,  # "accession",  # db_row[4]
                                                                "is_grouped",  # db_row[5]
                                                                "proteome_id",  # db_row[6]
                                                                "intensity"])  # db_row[7]

            psql.PostgreSQLConnection().returnConnection(db_conn)
        except Exception as err:
            if "db_cur" in locals():
                psql.PostgreSQLConnection().returnConnection(db_conn)
            raise err

    def __db_update(self):  # Question: Do we allow updates?
        if self._parent_dataset and self._parent_dataset.get_internal_id():
            # values have no id but are unique through their foreign keys
            # DELETE FROM table_name WHERE condition;
            # Todo: implement low priority
            # Todo: track how often it happens for reminder
            raise dlib.ABCDatatableError("UPDATE not implemented")  # ToDo: Implement __db_update(...)
        else:
            raise dlib.ABCDatatableError("Writing the PostgreSQLDataTable is not possible without stored parent dataset.")

    def read(self):
        self.__db_select()

    def write(self):
        # Todo: Think about and implement method!
        # in Other classes, if there is no id or does not exist --> attempt insert, otherwise 'update'
        # Here, check if values from the parent_dataset are present, if not insert otherwise 'update'
        # self.__db_insert()
        # self.__db_update()
        pass




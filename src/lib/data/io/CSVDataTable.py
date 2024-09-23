from __future__ import annotations

import errno
import os.path
import pandas as pd
import re

from lib.data import ABCDataTable, ABCDataTableError

class CSVDataTable(ABCDataTable):

    def __init__(self, path: str, name_index_col: str = ABCDataTable._row_index_name, regex_rule_data_col: str = ".+"):  # question: Should 'name_index_col' be configurable?
        super().__init__()

        self._path: str = path
        self._regex_rule_data_col: str = regex_rule_data_col
        self._name_index_col: str = name_index_col

        self._read_file()

    def _read_file(self, sep="\t"):
        self._reset()

        if not os.path.isfile(self._path):
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), self._path)
        else:
            self._test_columns(sep)
            data = pd.read_csv(self._path, sep=sep, header=0, index_col=self._name_index_col)

            if self._name_index_col != ABCDataTable._row_index_name:  # question: Should this be configurable?
                data.index.names = [ABCDataTable._row_index_name]

            shape_data = data.shape

            if shape_data[0] < 1:
                raise ABCDataTableError("There are no rows in the imported data table '{}'!".format(self._path))

            if shape_data[1] < 1:
                raise ABCDataTableError("There are no data columns in the imported data table '{}'!".format(self._path))

            self._data_wide = data
            self._data_long = None

    def _set_path(self, path: str):
        self._is_stored = False
        self._path = path

    def _test_columns(self, sep="\t"):
        self._data_columns = None

        if not os.path.isfile(self._path):
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), self._path)
        else:
            cols = pd.read_csv(self._path, sep=sep, nrows=1, header=None).loc[0].tolist()

            if self._name_index_col not in cols:
                raise ABCDataTableError("Unable to find the index column '{icol}' in '{fname}'.".format(icol=self._name_index_col, fname=self._path))

            # re_data_col = re.compile(self._regex_rule_data_col)  # fixme: why does this does not work compared to re.search(...)?
            # res_cols_data = [col for col in cols if re_data_col.match(col)]
            res_cols_data = [col for col in cols if re.search(self._regex_rule_data_col, col)]

            if any(res_cols_data):
                self._data_columns = res_cols_data
            else:
                raise ABCDataTableError("Unable to find any data columns using the regular expression '{}'".format(self._regex_rule_data_col))

    def _write_csv_file(self, sep="\t"):
        if not self._data_wide:
            self._change_to_wide()

        if not self._data_wide:
            raise ABCDataTableError("There is no data to write.")

        self._data_wide.to_csv(path_or_buf=self._path, sep=sep)

    def is_stored(self) -> bool:
        return False

    @staticmethod
    def get_n_values_with_dataset_id(dataset_id: int) -> int:
        return 0

    @staticmethod
    def get_n_samples_with_dataset_id(dataset_id: int) -> int:
        return 0

    def get_path(self) -> str:
        return self._path

    def create(self):
        self._write_csv_file()

    @classmethod
    def objectify_with_dataset_id(cls, dataset_id: int) -> CSVDataTable:
        raise ABCDataTableError("CSVDataTable objects can only be created using path to csv files.")

    @classmethod
    def objectify_with_dataset_label(cls, dataset_label: str) -> CSVDataTable:
        raise ABCDataTableError("CSVDataTable objects can only be created using path to csv files.")

    @classmethod
    def objectify_with_datatable(cls, datatable: ABCDataTable) -> CSVDataTable:
        raise ABCDataTableError("CSVDataTable objects can only be created using path to csv files.")

    def read(self):
        self._read_file()

    def write(self):
        self._write_csv_file()

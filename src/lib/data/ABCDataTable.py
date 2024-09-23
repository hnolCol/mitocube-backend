from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Self

import lib.data as dlib

import pandas as pd
# import copy
# from enum import Enum
# from typing import Self

# class CSVDataTableType(Enum):
#     UNKNOWN = -1
#     WIDE_FULL_DATA = 1

class ABCDataTableError(dlib.ABCDatasetError):
    pass


class ABCDataTableState(ABC):  # Question: Just a place holder for abstract state that could control actions in some methods

    def __init__(self, datatable: ABCDataTable):
        self._datatable = datatable

    @abstractmethod
    def read(self):
        pass

    @abstractmethod
    def write(self):
        pass


class ABCDataTable(ABC, dlib.FlexDataClass):

    _row_index_name: str = "Key"
    _column_name_long_values: str = "intensity"

    def __init__(self, parent_dataset: dlib.ABCDataset | None = None,
                 attributes_samples: dict[str, List[dlib.ABCTraitValue]] | None = None):  # ToDo: id into this object?
        self._data_columns: list[str] | None = None
        self._data_features: list[str] | None = None
        self._data_long: pd.DataFrame | None = None
        self._data_wide: pd.DataFrame | None = None
        self._parent_dataset: dlib.ABCDataset | None = parent_dataset
        self._attributes_samples: dict[str, List[dlib.ABCTraitValue]] | None = attributes_samples  # sample names as keys

    # FixMe: make it thread-safe!
    def _change_to_long(self, col_columns: str = "sample", col_feature: str = None, col_values: str | None = None):
        if col_values is None:
            col_values = self._column_name_long_values

        if self._data_wide is not None:
            data = self._data_wide.copy(deep=True)
            data[self._row_index_name] = data.index
            self._data_long = pd.melt(data,
                                      id_vars=self._row_index_name,  # fixme: Is it possible to use the row index instead?
                                      value_vars=self._data_columns,
                                      var_name=col_columns,
                                      value_name=col_values)

    # FixMe: make it thread-safe!
    # Question: Do we ever need wide?
    def _change_to_wide(self, col_columns: str = "sample", col_values: str | None = None):
        if col_values is None:
            col_values = self._column_name_long_values

        if self._data_long is not None:
            data = self._data_long.copy(deep=True)
            self._data_wide = data.pivot(index=self._row_index_name,
                                         columns=col_columns,
                                         values=col_values)

    @classmethod
    def _get_class_rulings(cls) -> Dict[str, Self]:
        import lib.data.sql.postgresql as sqllib
        return {"postgresql": sqllib.PostgreSQLDataTable}

    def _load_from_tbl(self, tbl: ABCDataTable):
        # self._dataset_id = tbl._dataset_id.copy()
        self._data_columns = tbl._data_long.copy(deep=True)
        self._data_long = tbl._data_long.copy(deep=True)
        self._data_wide = tbl._data_wide.copy(deep=True)

    def _reset(self):
        self._data_columns = None
        self._data_long = None
        self._data_wide = None

    @staticmethod
    def _test_attributes_samples_keys(data_table: ABCDataTable, attributes_samples: dict[str, List[dlib.ABCTraitValue]]):
        if len(attributes_samples) > 0:
            if not all(sample in data_table._data_columns for sample in attributes_samples.keys()):
                raise dlib.ABCDataTableError("Some sample names in provided attributes list do not exist in the DataTable.")

    def is_stored(self) -> bool:
        return self.get_n_samples_with_dataset_id(self._parent_dataset.get_internal_id()) > 0 if self._parent_dataset else False

    def get_unique_data_features(self) -> List[str]:
        if self._data_wide is not None:
            return self._data_wide.index.to_list()
        elif self._data_long is not None:
            return list(set(self._data_long[self._row_index_name]))
        else:
            return []  # Question: Or should be an exception be raised?
            # raise ABCDataTableError("No data is stored in the DataTable object!")

    @staticmethod
    @abstractmethod
    def get_n_values_with_dataset_id(dataset_id: int) -> int:
        pass

    @staticmethod
    @abstractmethod
    def get_n_samples_with_dataset_id(dataset_id: int) -> int:
        pass

    def get_data_column_names(self) -> list[str] | None:
        return self._data_columns

    # fixme: make it thread-safe!
    def get_features(self) -> list[str]:
        if not self.is_buffered():
            self.read()

        if self._data_wide is not None:
            return list(self._data_wide.index)
        elif self._data_long is not None:
            return list(self._data_long[self._row_index_name].unique())

    def get_long_table(self):
        if not self.is_buffered():
            self.read()

        if self._data_long is None:
            self._change_to_long()

        return self._data_long

    def get_wide_table(self):
        if not self.is_buffered():
            self.read()

        if self._data_wide is None:
            self._change_to_wide()

        return self._data_wide

    def is_buffered(self) -> bool:
        return self._data_long is not None or self._data_wide is not None

    def get_parent_dataset(self) -> dlib.ABCDataset | None:
        return self._parent_dataset

    def has_parent(self) -> bool:
        return self._parent_dataset is not None

    @classmethod
    @abstractmethod
    def objectify_with_dataset_id(cls, dataset_id: int) -> ABCDataTable:
        pass

    @classmethod
    @abstractmethod
    def objectify_with_dataset_label(cls, dataset_label: str) -> ABCDataTable:
        pass

    @classmethod
    @abstractmethod
    def objectify_with_datatable(cls, datatable: ABCDataTable) -> ABCDataTable:
        pass

    # FixMe: make it thread-safe!
    @abstractmethod
    def read(self):
        pass

    def set_parent_dataset(self, parent: dlib.ABCDataset | None):  # Question: Should it be possible for the dataset to reject change of parent? Exception here?
        self._parent_dataset = parent

    def set_samples_attributes(self, attributes_samples: dict[str, List[dlib.ABCTraitValue]] | None):
        ABCDataTable._test_attributes_samples_keys(data_table = self, attributes_samples = attributes_samples)
        self._attributes_samples = attributes_samples

    # fixme: make it thread-safe!
    def splitup_protein_groups(self, sep=","):
        raise ABCDataTableError("Method splitup_protein_groups(self, sep=", ") not implemented yet!")

        # ix = 0
        # print(self._data_wide.shape)
        # while ix < self._data_wide.shape[0]:
        #     if sep in self._data_wide.index[ix]:
        #         separated_pois = self._data_wide.index[ix].split(sep, -1)
        #         for separated_poi in separated_pois:
        #             if len(separated_poi) > 1:  # question: or > 0-3 ?
        #                 if separated_poi in self._data_wide.index:
        #                     raise ABCDatatableError("The feature '{}' originating from the protein group '{}' is already in the datatable. Only unique features allowed!".format(separated_poi, self._data_wide.index[ix]))
        #                 else:
        #                     # fixme: turns it from (10895, 60) to (10896, 10955)
        #                     row = pd.DataFrame(data = self._data_wide.iloc[ix],
        #                                        columns = [separated_poi], index=self._data_wide.index).T
        #                     self._data_wide = pd.concat([self._data_wide, row], axis=0, join='outer',
        #                               ignore_index=False, verify_integrity=True, sort=False, copy=None)
        #                     #
        #     ix += 1
        # print(self._data_wide.shape)

    @abstractmethod
    def write(self):
        pass

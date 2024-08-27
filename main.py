import datetime

from config import get_system_settings
from lib.data import ABCDatabase, ABCDataset
from lib.data.panda import PandaFeatureDatabase
from lib.data.io import CSVDataTable
from lib.data.sql.postgresql import PostgreSQLDataset, PostgreSQLFeatureDatabase

print("=========================================")
print(__name__)
print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
print("{timestamp}.".format(timestamp=datetime.datetime.now().strftime("%A the %Y-%m-%d (week %V), %X")))
print(".........................................")
CONF = get_system_settings()
print(CONF)
print("=========================================")

print("\n\n\n=========================================")
print("ABCDatabase()")
print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
db_class = ABCDatabase.get_database_class()
print(db_class)
db_class = ABCDatabase.get_database_class()
print(db_class)
print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
print(db_class())
print("=========================================")


print("\n\n\n=========================================")
print("PostgreSQLFeatureDatabase()")
print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
db_features = PostgreSQLFeatureDatabase()  # todo: create 'init'/first loading method
db_features.read()
print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
print(db_features._cached_features.head().to_string())
print("=========================================")
# db = ABCDatabase.get_database()  # todo: create 'init'/first loading method
# print(db)


print("\n\n\n=========================================")
print("PostgreSQLDataset(")
print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
print(PostgreSQLDataset.does_exist_with_labels(["BuXOSlIl6G", "KUbPyK1ASG", "QPa98BBMhS", "VSTFFlpDMyDG", "YKLJPnEwP8"]))
print("=========================================")

print("\n\n\n=========================================")
print("CSVDataTable(")
print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
csv = CSVDataTable(path="/home/andreaslindner/Projects/MitoCube/GitHub/mitocube-backend/resources/data/BuXOSlIl6G/data.txt",
                   regex_rule_data_col="^[0-9]{8}[_\\.-]",
                   name_index_col="Key")

print(len(csv.get_features()))
print("=========================================")

# csv.splitup_protein_groups(sep="7")
# Strategie|Command|State|Proxy for transformation or imputation? https://refactoring.guru/design-patterns/proxy/python/example

# ds = ABCDataset.build_from_scratch(data=csv, state=None, title="None", owner_user=None, owner_group=None, contact_email="None", parent_project=None)
# print(ds)
# print(ds._data.get_parent_dataset().get_internal_id())
# # print(ds._internal_id)
# print(ds._external_id)
# print(ds._title)
# ds.write()

print("=========================================")

'''

SELECT internal_id, external_id, project_id, title, owner_id, state FROM datasets;

SELECT id, dataset_id, event_type, timestamp, owner_id, contact_user_id, comment FROM dataset_timeline;

SELECT id, dataset_id, tag, text, language FROM metatexts;

SELECT id, dataset_id, label FROM samples;

SELECT values, transformation, oi_id, sample_id, dataset_id FROM sample_values;

SELECT id, sample_id, label FROM replicates;

SELECT id, label, type, organism_id, proteome_id, is_grouped FROM ois;

SELECT grouped_oi_id, oi_id FROM nm_grouped_ois;

SELECT id, name, address, ... FROM institutes;

SELECT institute_id, user_id FROM nm_institutes_users;

SELECT id, username, password, salt, firstname, middlename, lastname, email, email_recovery, is_login_allowed, is_email_verified, research_group, role, base64_image, base64_preview, created_on, last_login_on, expires_after FROM sec_users; 

SELECT id, parent_id, tag, text, priority, allow_as_filter, allow_for_dataset, allow_for_genotype, allow_for_qc, ..., allow_features, allow_value FROM attributes;

SELECT id, attribute_id, tag, text, keyword, description, ... FROM traits; how to store values?

SELECT id, dataset_id, project_id, user_id, url;

SELECT id, dataset_id, timestamp, n_peptides, n_pg FROM qc;

SELECT id, label, text, description FROM instruments

SELECT dataset_id, trait_id, feature_value, string_value FROM nm_trait_dataset;

SELECT sample_id, trait_id, feature_value, string_value FROM nm_trait_sample;

SELECT qc_id, attribute_value_id, feature_value, string_value FROM nm_attribute_value_qc;

SELECT id, label, text FROM categories;

SELECT category_id, attribute_id FROM nm_attribute_category;

SELECT id, label, text, FROM genotype;

SELECT uid, started_on, expires_after, user_id, ip, system, browser, last_use_on FROM sec_user_session;
'''
#
# class Dataset:
#     def __init__(self, data):
#         self._internal_id: int = -1
#         self._external_id: str = "ksdjfldshjflsk"
#
#         self._data_long = None  # DataTable
#         self._data_wide = None  # DataTable
#
#         # query for one (or more protein), found in multiple samples across multiple datasets projects
#         # 1) data of a project; rows: proteins / peptides | columns: samples
#         # 2) search for a protein; rows: matching proteins / peptides | columns: samples
#
#         # Cell: values, can be imputed, missing, raw, corrected, transformed
#
# class Project:
#     def __init__(self):
#         self._internal_id: int = -1
#         self._external_id: str = "ksdjfldshjflsk"
#
#         self._datasets: dict[str, Dataset] | None = None  # Dict[str, Dataset]
#         pass
#
#     def __repr__(self) -> str:  # Return a string containing a printable representation of an object.
#         return "Something about the Project"
#
#     def __iter__(self):
#         self.__it = 1
#         return self
#
#     def __next__(self):
#         if self.__it < 42:
#             value = self.__it
#             self.__it += 1
#             return value
#         else:
#             raise StopIteration
#
#
# # obj = Project()
# # obj_iter = iter(obj)
# #
# # for value in obj_iter:
# #     print(value)
#
#
# import numpy as np
# import pandas as pd
#
# # https://tryolabs.com/blog/2023/02/08/top-5-tips-to-make-your-pandas-code-absurdly-fast
# # https://pandas.pydata.org/docs/user_guide/basics.html
# # https://scikit-learn.org/stable/modules/generated/sklearn.impute.SimpleImputer.html#sklearn.impute.SimpleImputer
#
# @pd.api.extensions.register_dataframe_accessor("testi")
# class ScienceAccessor:
#     def __init__(self, pandas_obj):
#         print("> ScienceAccessor.__init__(...)")
#         self._validate(pandas_obj)
#         self._obj = pandas_obj
#
#     @staticmethod
#     def _validate(obj):
#         # verify there is a column latitude and a column longitude
#         #if "latitude" not in obj.columns or "longitude" not in obj.columns:
#         #    raise AttributeError("Must have 'latitude' and 'longitude'.")
#         pass
#
#     @property
#     def log2(self):
#         print("> log2(self)")
#         # return the geographic center point of this DataFrame
#         return self._obj.apply(np.log2)  # return (float(lon.mean()), float(lat.mean()))
#
#     def impute2(self, mean: float, sd: float):
#         print("> impute2")
#         n_nans = self._obj.isna().sum().sum()
#         imputed_values = np.random.normal(loc=mean, scale=sd, size=n_nans)
#
#         iter_imputed_values = iter(imputed_values)
#
#         def replaceValues(value):
#             if pd.isna(value):
#                 return next(iter_imputed_values)
#             return value
#
#         return dTable.map(replaceValues)
#
#     @property  # as function?
#     def impute(self):
#         print("> impute")
#         n_nans = self._obj.isna().sum().sum()
#         imputed_values = np.random.normal(loc=33, scale=1, size=n_nans)
#
#         iter_imputed_values = iter(imputed_values)
#
#         def replaceValues(value):
#             if pd.isna(value):
#                 return next(iter_imputed_values)
#             return value
#
#         return dTable.map(replaceValues)
#
#
# dTable = np.random.normal(loc = 4.0, scale = 1.0, size = (10, 42))
# dTable_replacement = np.random.normal(loc = 4.0, scale = 1.0, size = 21)
# dTable_replacement_2D = np.random.normal(loc = 444.0, scale = 1.0, size = (10, 42))
# # print(dTable)
#
# # print(np.random.normal(loc = 4.0, scale = 1.0, size = 1)[0])
#
# dTable = pd.DataFrame(data = dTable)
# dTable_replacement = pd.DataFrame(data = dTable_replacement)
# dTable_replacement_2D = pd.DataFrame(data = dTable_replacement_2D)
# # print(dTable)
#
# ixs_row_na = np.random.randint(1, dTable.shape[0], 21)
# ixs_col_na = np.random.randint(1, dTable.shape[1], 21)
#
#
# for ix in range(21):
#     dTable.iloc[ixs_row_na[ix], ixs_col_na[ix]] = np.nan
#
#
# # class Dataset? (? Heap)
# #   currentDim = raw or log or something
# #
# #  myDs = new Dataset(data)
# #  myDs.transform("log2")
# #
# # class DataPoint
# #    parentDataset = myDs
# #    raw = 123
# #    log = 6.942515
# #    log_method = log2
# #    is_imputed = false
# #    imputed_value = raw (or imputed value)
# #    __value() if myDs.method == "log2" return self.log
# #    or __value() self.getMethod() and before my.getMethod = log # or work with index within Dataset !!! possible to work with pointers?
# # https://numpy.org/doc/stable/reference/random/generated/numpy.random.normal.html

from datetime import datetime, timedelta
import os
import sys

from config import get_system_settings

import lib.data as dlib
import lib.data.sql.postgresql as psql
from lib.data.io import CSVDataTable, JSONDataset
from lib.data.io.JSONAttributes import JSONAttributes

print("\n")

print("=========================================")
print("Install & Migrate: {name}".format(name = __name__))
print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
print("{timestamp}.".format(timestamp = datetime.now().strftime("%A the %Y-%m-%d (week %V), %X")))
print(".........................................")
CONF = get_system_settings()
print(CONF)
print("=========================================")

print("\n\n\n")

print("=========================================")
print("Prepare the FeatureDatabase")
print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
print("{timestamp}.".format(timestamp = datetime.now().strftime("%A the %Y-%m-%d (week %V), %X")))
print(".........................................")
db_features = psql.PostgreSQLFeatureDatabase()  # todo: create 'init'/first loading method
db_features.read()
print(".........................................")
print(db_features._cached_features.head().to_string())
print("=========================================")

print("=========================================")
print("Check for installed users")
print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
print("{timestamp}.".format(timestamp = datetime.now().strftime("%A the %Y-%m-%d (week %V), %X")))
print(".........................................")
db_users: dlib.ABCUser = dlib.ABCUser.get_class()
print(db_users.get_user_names())
print(".........................................")
users = db_users.get_users()
print(users)
print(".........................................")
if not db_users.does_exist_with_username("superuser"):
    print("  (!) no 'superuser' in the system. creating one with the password '{pwd}'".format(pwd="bamboozle"))
    superuser = db_users(db_id = None, username = "superuser", research_group = None,
                         firstname = "super", lastname = "user",
                         email = "andreas.lindner@uni-bonn.de",
                         base64_image = None, profile_text = None, orcid = None, url = None,
                         allow_login = True, expires_after = datetime.now() + timedelta(weeks=52.1775*999))
    superuser.write()
    superuser.write_password("bamboozle")
else:
    superuser = db_users.objectify_with_username("superuser")

print(superuser)

if not superuser.test_password("bamboozle"):
    print("  (!) configured password for 'superuser' is not correctly stored in db!")
else:
    print("  (i) configured password is correctly stored for 'superuser'")

if not superuser.is_login_allowed():
    print("  (!) 'superuser' is not allowed to login!")
else:
    print("  (i) 'superuser' is allowed to login")
print("=========================================")

print("\n\n\n")

print("=========================================")
print("Import & Install Attributes with Traits")
print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
print("{timestamp}.".format(timestamp = datetime.now().strftime("%A the %Y-%m-%d (week %V), %X")))
print(".........................................")
json_attributes = JSONAttributes(path_json_file = "/home/andreaslindner/Projects/MitoCube/DB_Interface_2024/resources/installation/attributes_examples.json")
json_attributes.read(ignore_missing_parent_attributes = True)
print("? here")
json_attributes.write()
print("? here")
print("=========================================")

print("\n\n\n")

print("=========================================")
print("Import existing Datasets")
print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
print("{timestamp}.".format(timestamp = datetime.now().strftime("%A the %Y-%m-%d (week %V), %X")))
print(".........................................")

list_dataset_ids = {}
str_parent_folder = "/home/andreaslindner/Projects/MitoCube/GitHub/mitocube-backend/resources/data"

db_datasets = dlib.ABCDataset.get_class()

for str_dir in os.listdir(str_parent_folder):
    if os.path.join(str_parent_folder, str_dir):
        if os.path.isfile(os.path.join(str_parent_folder, str_dir, "params.json")):
            list_dataset_ids[str_dir] = os.path.join(str_parent_folder, str_dir)


for dataset_id, dataset_path in list_dataset_ids.items():
    print("\n> processing {did} ({path})".format(did = dataset_id, path = dataset_path))

    if db_datasets.does_exist_with_label(dataset_id):
        print("  (!) does exist already in database, skipping import")
    else:
        print("  (i) does not exist in database, prepare import")

        if os.path.isfile(os.path.join(str_parent_folder, dataset_id, "data.txt")):
            csv_dataset = CSVDataTable(path=os.path.join(str_parent_folder, dataset_id, "data.txt"),
                                       regex_rule_data_col="^[0-9]{8}[_\\.-]",
                                       name_index_col="Key")

            print("  (i) imported 'data.txt' with n = {n} features".format(n=len(csv_dataset.get_features())))

            json_dataset = JSONDataset.objectify_with_json(path = os.path.join(str_parent_folder, dataset_id, "params.json"),
                                                           owner_user = superuser,
                                                           data_table = csv_dataset,
                                                           class_target = psql.PostgreSQLDataset,  # Fixme: fix typing issue here, what is the type of a (class) class-object?
                                                           class_attribute_traits = psql.PostgreSQLTrait)  # Fixme: fix typing issue here

            psql_data = psql.PostgreSQLDataTable.objectify_with_datatable(csv_dataset)  # "Casts" the CSV data table to a postgresql data table
            # psql_data.set_batches(xxx)
            # psql_data.set_replicates(xxx)

            print(psql_data)

            pgsql_dataset = psql.PostgreSQLDataset.objectify_with_dataset(json_dataset)  # "Casts" the json data set to a postgresql dataset
            pgsql_dataset.set_data(data = psql_data)  # assigns the data table to the dataset
            pgsql_dataset.write(write_datatable = True)  # writes everything to the db. Attributes etc. require to be postgresql at this point but JSONDataset takes partly care of it already

            print("  (i) imported 'params.json' with n = {n} features".format(n=0))


print("=========================================")

print("\n\n\n")

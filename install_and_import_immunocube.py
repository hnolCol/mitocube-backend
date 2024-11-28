import os
import sys
import glob

from typing import Dict, List, Type
from datetime import datetime, timedelta
import numbers

import re
import json

import numpy as np
import pandas as pd

from config import get_system_settings

import lib.data as dlib
import lib.data.sql.postgresql as psql
# from lib.data.io import CSVDataTable, JSONDataset
from lib.data.io.JSONAttributes import CSVAttributImporter

data_import_users = {"superuser", {"firstname": "super",
                                   "lastname": "user",
                                   "email": "andreas.lindner@uni-bonn.de",
                                   "base64_image": None,
                                   "profile_text": None,
                                   "orcid": None,
                                   "url": None,
                                   "allow_login": True,
                                   "expires_after": datetime.now() + timedelta(weeks=52.1775*999),
                                   "password": "bamboozle"}}

data_import_attributes = {"default", {"comment": "Used in the CoreCube",
                                      "file_atts": "attributes_default_20241126.csv",
                                      "file_traits": "traits_default_20241126.csv"},
                          "immunocube", {"comment": "Used mostly in the ImmunoCube",
                                         "file_atts": "attributes_immunocube_20241126.csv",
                                         "file_traits": "traits_immunocube_20241126.csv"}
                          }

print("\n")

print("=========================================")
print("Install DB & add Datasets: {name}".format(name = __name__))
print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
print("{timestamp}.".format(timestamp = datetime.now().strftime("%A the %Y-%m-%d (week %V), %X")))
print(".........................................")
CONF = get_system_settings()
print(CONF)
print("=========================================")

print("\n\n\n")


print("\n\n\n")

print("=========================================")
print("Check for installed users")
print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
print("{timestamp}.".format(timestamp = datetime.now().strftime("%A the %Y-%m-%d (week %V), %X")))
print(".........................................")
db_users: Type[dlib.ABCUser] = dlib.ABCUser.get_class()
print(db_users.get_user_names())
print(".........................................")
users = db_users.get_users()
print(users)

for username, item in data_import_users.items():
    print(".........................................")
    if not db_users.does_exist_with_username(username):
        print("  (!) no 'superuser' in the system. creating one with the password '{pwd}'".format(pwd="bamboozle"))
        user = db_users(db_id = None, username = username, research_group = None,
                        firstname = item["firstname"], lastname = item["lastname"], email = item["email"],
                        base64_image = item["base64_image"], profile_text = item["profile_text"],
                        orcid = item["orcid"], url = item["url"],
                        allow_login = item["allow_login"],
                        expires_after = item["expires_after"])
        user.write_to_db()

        user = db_users.objectify_with_username("superuser")

    print(user)

    if not user._test_password("bamboozle"):
        print("  (!) configured password for 'superuser' is not correctly stored in db!")
    else:
        print("  (i) Configured password is correctly stored for 'superuser'")

    if not user.is_login_allowed():
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
for label, item in data_import_attributes.items():
    print(".........................................")
    print("  (i) Attempt to import Attributes and Traits for '{label}':".format(label=label))
    csv_attributes = CSVAttributImporter(attribute_file = item["file_atts"], trait_file = item["file_traits"])
    csv_attributes.read(ignore_missing_parent_attributes = True)
    csv_attributes.write()

print("=========================================")

print("\n\n\n")


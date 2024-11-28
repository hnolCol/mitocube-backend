
from datetime import datetime, timedelta
import glob
# import os
# import sys
import re
# import json
import numpy as np
from typing import Dict, List, Type
import numbers

from config import get_system_settings

import pandas as pd

import lib.data as dlib
import lib.data.sql.postgresql as psql
# from lib.data.io import CSVDataTable, JSONDataset
# from lib.data.io.JSONAttributes import JSONAttributes

print("\n")

print("=========================================")
print("Install ImmunoCube Munich Data: {name}".format(name = __name__))
print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
print("{timestamp}.".format(timestamp = datetime.now().strftime("%A the %Y-%m-%d (week %V), %X")))
print(".........................................")
CONF = get_system_settings()
print(CONF)
print(".........................................")


path_import = "/home/andreaslindner/Projects/MitoCube/ImmunoCube_Data/Raw_Import"

files = glob.glob(path_import + "/*/proteinGroups.txt", recursive = True)

print(files)
print("=========================================")

print("\n\n")
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

print("\n\n")
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
print(".........................................")
if not db_users.does_exist_with_username("superuser"):
    print("  (!) no 'superuser' in the system. creating one with the password '{pwd}'".format(pwd="bamboozle"))
    superuser = db_users(db_id = None, username = "superuser", research_group = None,
                         firstname = "super", lastname = "user",
                         email = "andreas.lindner@ukbonn.de",
                         base64_image = None, profile_text = None, orcid = None, url = None,
                         allow_login = True, expires_after = datetime.now() + timedelta(weeks=52.1775*999))
    superuser.write_to_db()
    superuser.write_password("bamboozle")
else:
    superuser = db_users.objectify_with_username("superuser")

print(superuser)

if not superuser._test_password("bamboozle"):
    print("  (!) configured password for 'superuser' is not correctly stored in db!")
else:
    print("  (i) configured password is correctly stored for 'superuser'")

if not superuser.is_login_allowed():
    print("  (!) 'superuser' is not allowed to login!")
else:
    print("  (i) 'superuser' is allowed to login")
print(".........................................")
if not db_users.does_exist_with_username("felix.meissner"):
    print("  (!) no 'superuser' in the system. creating one with the password '{pwd}'".format(pwd="bamboozle"))
    felix = db_users(db_id = None, username = "felix.meissner", research_group = None,
                     firstname = "Felix", lastname = "Meissner",
                     email = "felix.meissner@uni-bonn.de",
                     base64_image = None, profile_text = None, orcid = "0000-0003-1000-7989", url = "https://www.iiibonn.de/felix-meissner-lab/felix-meissner-lab-science",
                     allow_login = True, expires_after = datetime.now() + timedelta(weeks=52.1775*999))
    felix.write_to_db()
    felix.write_password("bamboozle")
else:
    felix = db_users.objectify_with_username("felix.meissner")

print(felix)

if not felix._test_password("bamboozle"):
    print("  (!) configured password for 'superuser' is not correctly stored in db!")
else:
    print("  (i) configured password is correctly stored for 'superuser'")

if not felix.is_login_allowed():
    print("  (!) 'felix' is not allowed to login!")
else:
    print("  (i) 'felix' is allowed to login")
print(".........................................")
if not db_users.does_exist_with_username("andreas.lindner"):
    print("  (!) no 'superuser' in the system. creating one with the password '{pwd}'".format(pwd="bamboozle"))
    andreas = db_users(db_id = None, username = "andreas.lindner", research_group = None,
                       firstname = "Andreas", lastname = "Lindner",
                       email = "andreas.lindner@uni-bonn.de",
                       base64_image = None, profile_text = None, orcid = "0000-0003-1590-3547", url = None,
                       allow_login = True, expires_after = datetime.now() + timedelta(weeks=52.1775*999))
    andreas.write_to_db()
    andreas.write_password("bamboozle")
else:
    andreas = db_users.objectify_with_username("andreas.lindner")

print(andreas)

if not andreas._test_password("bamboozle"):
    print("  (!) configured password for 'superuser' is not correctly stored in db!")
else:
    print("  (i) configured password is correctly stored for 'superuser'")

if not andreas.is_login_allowed():
    print("  (!) 'andreas.lindner' is not allowed to login!")
else:
    print("  (i) 'andreas.lindner' is allowed to login")
print("=========================================")


meta_info = {"20240823-214048_pmn-degranulome": {"species": "human",
                                                 "details": "PMN Degranulome",
                                                 "experiment": "Secretome",
                                                 "title": "PMN Degranulome",
                                                 "created_on": datetime.strptime("2024-12-12", "%Y-%m-%d"),
                                                 "samples": []
                                                 },
             "20240827-031059_unconventional-1": {"species": "mouse",
                                                  "details": "unconventional 1",
                                                  "experiment": "Secretome",
                                                  "title": "Unconventional Mouse Secretome",
                                                  "created_on": datetime.strptime("2024-12-12", "%Y-%m-%d"),
                                                  "samples": []
                                                  },
             "20240828-155925_mast-cell-degranulome": {"species": "mouse",
                                                       "details": "mast cell degranulome",
                                                       "experiment": "Secretome",
                                                       "title": "Mast Cell Degranulome",
                                                       "created_on": datetime.strptime("2024-12-12", "%Y-%m-%d"),
                                                       "samples": []
                                                       },
             "20240830-055604_neutrophil-degranulome": {"species": "human",
                                                        "details": "Neutrophil Degranulome (Falko)",
                                                        "experiment": "Secretome",
                                                        "title": "Neutrophil Degranulome",
                                                        "created_on": datetime.strptime("2024-12-12", "%Y-%m-%d"),
                                                        "samples": []
                                                        },
             "20240830-125656_monocytes-alt-inflammasome": {"species": "human",
                                                            "details": "monocytes alternative inflammasome",
                                                            "experiment": "Secretome",
                                                            "title": "Alternative Monocyte Inflammasome",
                                                            "created_on": datetime.strptime("2024-12-12", "%Y-%m-%d"),
                                                            "samples": []
                                                            },
             "20240830-170343_science-paper": {"species": "mouse",
                                               "details": "Science paper",
                                               "experiment": "Secretome",
                                               "title": "Direct proteomic quantification of the secretome of activated immune cells",
                                               "created_on": datetime.strptime("2024-12-12", "%Y-%m-%d"),
                                               "samples": []
                                               },
             "20240903-172525_meeras-paper-nlrp3-human": {"species": "human",
                                                          "details": "Meeras paper Nlrp3 human",
                                                          "experiment": "Secretome",
                                                          "title": "Proteomics reveals distinct mechanisms regulating the release of cytokines and alarmins during pyroptosis",
                                                          "created_on": datetime.strptime("2024-12-12", "%Y-%m-%d"),
                                                          "samples": []
                                                          },
             # "20240906-144523_degranulome-mast-0015": {"species": "mouse",
             #                                           "details": "Degranulome (Mast cells)",
             #                                           "experiment": "Secretome",
             #                                           "title": "Mast Cell Degranulome 15 ",
             #                                           "created_on": datetime.strptime("2024-12-12", "%Y-%m-%d"),
             #                                           "samples": []
             #                                           },
             "20240907-004106_degranulome-0016": {"species": "mouse",
                                                  "details": "Degranulome (Mast cells)",
                                                  "experiment": "Secretome",
                                                  "title": "Mast Cell Degranulome 16",
                                                  "created_on": datetime.strptime("2024-12-12", "%Y-%m-%d"),
                                                  "samples": []
                                                  },
             "20240907-154548_bmm-bmmcs": {"species": "mouse",
                                           "details": "BMMs,  BMMCs",
                                           "experiment": "Proteome",
                                           "title": "Bone Marrow-Derived (Mast Cells)",
                                           "created_on": datetime.strptime("2024-12-12", "%Y-%m-%d"),
                                           "samples": []
                                           }
             }

attribute_info = {"att_knockout_stat": {"text": "Knockout", "priority" :100},
                  "att_organism": {"text": "organism", "priority": 100},
                  "att_timepoint": {"text": "Timepoint", "priority": 100},
                  "att_other": {"text": "Other", "priority": 1000},
                  "att_treatment": {"text": "Treatment", "priority": 100}}

trait_info = {"att_other:neg": {"attribute_tag": "att_other", "tag": "neg", "text": "neg", "keyword": "neg", "description": "Negative"},
              "att_other:pos": {"attribute_tag": "att_other", "tag": "pos", "text": "pos", "keyword": "pos", "description": "Positive"},
              "att_other:Control": {"attribute_tag": "att_other", "tag": "Control", "text": "Control", "keyword": None, "description": "Control"},
              "att_organism:human": {"attribute_tag": "att_organism", "tag": "human", "text": "Human", "keyword": "human", "description": "Homo Sapiens (Human)"},
              "att_organism:mouse": {"attribute_tag": "att_organism", "tag": "mouse", "text": "Mouse", "keyword": "mouse", "description": "Mus musculus (Mouse)"},
              "att_knockout_stat:DKO": {"attribute_tag": "att_knockout_stat", "tag": "DKO", "text": "Double Knockout", "keyword": "dko", "description": "Double Knockout (DKO)"},
              "att_knockout_stat:MYD88": {"attribute_tag": "att_knockout_stat", "tag": "MYD88", "text": "Myd88 Knockout", "keyword": "myd88", "description": "Myd88 Knockout"},
              "att_knockout_stat:TRIF": {"attribute_tag": "att_knockout_stat", "tag": "TRIF", "text": "Trif Knockout", "keyword": "trif", "description": "Trif Knockout"},
              "att_knockout_stat:WT": {"attribute_tag": "att_knockout_stat", "tag": "WT", "text": "Wild Type", "keyword": "wt", "description": "Wild Type"},
              "att_knockout_stat:Control": {"attribute_tag": "att_knockout_stat", "tag": "Control", "text": "Control", "keyword": "control", "description": "Control"},
              "att_timepoint:1h": {"attribute_tag": "att_timepoint", "tag": "1h", "text": "1 h", "keyword": "1h", "description": "1 hour timepoint"},
              "att_timepoint:2h": {"attribute_tag": "att_timepoint", "tag": "2h", "text": "2 h", "keyword": "2h", "description": "2 hour timepoint"},
              "att_timepoint:4h": {"attribute_tag": "att_timepoint", "tag": "4h", "text": "4 h", "keyword": "4h", "description": "4 hour timepoint"},
              "att_timepoint:8h": {"attribute_tag": "att_timepoint", "tag": "8h", "text": "8 h", "keyword": "8h", "description": "8 hour timepoint"},
              "att_timepoint:16h": {"attribute_tag": "att_timepoint", "tag": "16h", "text": "16 h", "keyword": "16h", "description": "16 hour timepoint"},
              "att_timepoint:18h": {"attribute_tag": "att_timepoint", "tag": "18h", "text": "18 h", "keyword": "17h", "description": "18 hour timepoint"},
              "att_timepoint:10": {"attribute_tag": "att_timepoint", "tag": "10", "text": "10 minutes", "keyword": "10m", "description": "10 minute timepoint"},
              "att_timepoint:50": {"attribute_tag": "att_timepoint", "tag": "50", "text": "50 minutes", "keyword": "50m", "description": "50 minute timepoint"},
              "att_timepoint:80": {"attribute_tag": "att_timepoint", "tag": "80", "text": "80 minutes", "keyword": "80m", "description": "80 minute timepoint"},
              "att_treatment:Control": {"attribute_tag": "att_treatment", "tag": "Control", "text": "Control", "keyword": "Control", "description": "Control / No Treatment"},
              "att_treatment:ATP": {"attribute_tag": "att_treatment", "tag": "ATP", "text": "ATP", "keyword": "ATP", "description": "Adenosine triphosphate"},
              "att_treatment:BFA": {"attribute_tag": "att_treatment", "tag": "BFA", "text": "Brefeldin A", "keyword": "BFA", "description": "Brefeldin A"},
              "att_treatment:CTB": {"attribute_tag": "att_treatment", "tag": "CTB", "text": "CTB", "keyword": "CTB", "description": "CTB"},
              "att_treatment:LPS": {"attribute_tag": "att_treatment", "tag": "LPS", "text": "Lipopolysaccharide", "keyword": "LPS", "description": "Lipopolysaccharide"},
              "att_treatment:PMA": {"attribute_tag": "att_treatment", "tag": "PMA", "text": "PMA", "keyword": "PMA", "description": "phorbol 12-myristate 13-acetate"},
              "att_treatment:PIC": {"attribute_tag": "att_treatment", "tag": "PIC", "text": "Poly(I:C)", "keyword": "PIC", "description": "Polyinosinic:polycytidylic acid"},
              "att_treatment:ZYM": {"attribute_tag": "att_treatment", "tag": "ZYM", "text": "Zymosan", "keyword": "ZYM", "description": "Zymosan"},
              "att_treatment:fMLP": {"attribute_tag": "att_treatment", "tag": "fMLP", "text": "fMLP", "keyword": "fMLP", "description": "formyl-methionyl-leucyl-phenylalanine"},
              "att_treatment:ifna": {"attribute_tag": "att_treatment", "tag": "ifna", "text": "IFN-alpha", "keyword": "ifna", "description": "IFN-alpha"},
              "att_treatment:zymo": {"attribute_tag": "att_treatment", "tag": "zymo", "text": "zymo", "keyword": "zymo", "description": "zymo"},
              "att_treatment:Nigericin": {"attribute_tag": "att_treatment", "tag": "Nigericin", "text": "Nigericin", "keyword": "Nigericin", "description": "Nigericin"},
              "att_treatment:LPS_Nigericin_Brefeldin-A": {"attribute_tag": "att_treatment", "tag": "LPS_Nigericin_Brefeldin-A", "text": "LPS + Nigericin + Brefeldin-A", "keyword": None, "description": "LPS + Nigericin + Brefeldin-A"},
              "att_treatment:LPS_Brefeldin-A": {"attribute_tag": "att_treatment", "tag": "LPS_Brefeldin-A", "text": "LPS + Brefeldin-A", "keyword": None, "description": "LPS + Brefeldin-A"},
              "att_treatment:Nigericin_Brefeldin-A": {"attribute_tag": "att_treatment", "tag": "Nigericin_Brefeldin-A", "text": "Nigericin + Brefeldin-A", "keyword": None, "description": "Nigericin + Brefeldin-A"},
              "att_treatment:LPS_A15_CTB": {"attribute_tag": "att_treatment", "tag": "LPS_A15_CTB", "text": "LPS + A15 + CTB", "keyword": None, "description": "LPS + A15 + CTB"},
              "att_treatment:LPS_A30_CTB": {"attribute_tag": "att_treatment", "tag": "LPS_A30_CTB", "text": "LPS + A30 + CTB", "keyword": None, "description": "LPS + A30 + CTB"},
              "att_treatment:LPS_A60_CTB": {"attribute_tag": "att_treatment", "tag": "LPS_A60_CTB", "text": "LPS + A6 + CTB", "keyword": None, "description": "LPS + A6 + CTB"},
              "att_treatment:LPS_Nigericin": {"attribute_tag": "att_treatment", "tag": "LPS_Nigericin", "text": "LPS + Nigericin", "keyword": None, "description": "LPS + Nigericin"},
              "att_treatment:LPS_A60_Nigericin": {"attribute_tag": "att_treatment", "tag": "LPS_A60_Nigericin", "text": "LPS + A60 + Nigericin", "keyword": None, "description": "LPS + A60 + Nigericin"},
              "att_treatment:LPS_ATP": {"attribute_tag": "att_treatment", "tag": "LPS_ATP", "text": "LPS + ATP", "keyword": None, "description": "LPS + ATP"},
              "att_treatment:LPS_BFA": {"attribute_tag": "att_treatment", "tag": "LPS_BFA", "text": "LPS + BFA", "keyword": None, "description": "LPS_BFA"},
              "att_treatment:LPS_CTB": {"attribute_tag": "att_treatment", "tag": "LPS_CTB", "text": "LPS + CTP", "keyword": None, "description": "LPS + CTP"},
              "att_treatment:LPS_A15_ATP": {"attribute_tag": "att_treatment", "tag": "LPS_A15_ATP", "text": "LPS + A15 + ATP", "keyword": None, "description": "LPS + A15 + ATP"},
              "att_treatment:LPS_A15_Nigericin": {"attribute_tag": "att_treatment", "tag": "LPS_A15_Nigericin", "text": "LPS + A15 + Nigericin", "keyword": None, "description": "LPS + A15 + Nigericin"},
              "att_treatment:LPS_A30_ATP": {"attribute_tag": "att_treatment", "tag": "LPS_A30_ATP", "text": "LPS + A30 + ATP", "keyword": None, "description": "LPS + A30 + ATP"},
              "att_treatment:LPS_A30_Nigericin": {"attribute_tag": "att_treatment", "tag": "LPS_A30_Nigericin", "text": "LPS + A30 + Nigericin", "keyword": None, "description": "LPS + A30 + Nigericin"},
              "att_treatment:LPS_A60_ATP": {"attribute_tag": "att_treatment", "tag": "LPS_A60_ATP", "text": "LPS + A60 + ATP", "keyword": None, "description": "LPS + A60 + ATP"},
              "att_treatment:ATP_Brefeldin-A": {"attribute_tag": "att_treatment", "tag": "ATP_Brefeldin-A", "text": "ATP+ Brefeldin-A", "keyword": None, "description": "ATP_Brefeldin-A"},
              "att_treatment:LPS_ATP_Brefeldin-A": {"attribute_tag": "att_treatment", "tag": "LPS_ATP_Brefeldin-A", "text": "LPS + ATP + Brefeldin-A", "keyword": None, "description": "LPS_ATP_Brefeldin-A"},
              "att_treatment:33": {"attribute_tag": "att_treatment", "tag": "33", "text": "33", "keyword": None, "description": "33"}}

print("\n\n")
print("=========================================")
print("Data Files")
print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
print(" > Import pre-defined data files and determine sample names ...")
re_column_search = re.compile("^Intensity (.*)$")

panda_helper = pd.DataFrame({"dataset": [], "sample": []})

for file in files:
    print("> Importing file '{}' ...".format(file))
    dataset = re.search(".*/(.*)/proteinGroups\\.txt$", file).group(1)
    df = pd.read_csv(file, sep="\t")

    data_columns = list(filter(re_column_search.match, list(df.columns)))
    data_selected_columns = ["Protein IDs"] + data_columns
    sample_names = [re_column_search.search(str_column).group(1) for str_column in data_columns]

    empty_columns = df[data_columns].columns[(df[data_columns] == 0).all()]
    if len(empty_columns) > 0:
        print(" (!!!) The columns '{}' are empty!".format(empty_columns.to_list()))

    empty_columns = df[data_columns].columns[(np.isnan(df[data_columns])).all()]
    if len(empty_columns) > 0:
        print(" (!!!) The columns '{}' are empty!".format(empty_columns.to_list()))

    if dataset not in meta_info.keys():
        print(" (!) The dataset '{}' has a folder / file struture but no information in the meta JSON. Skip!")
        continue

    meta_info[dataset]["samples"] = sample_names

    # "Protein IDs"  "Protein names"  "Gene names" "Number of proteins"  "Q-value" "Score" "Reverse", "Potential contaminant"
    df = df[["Protein IDs", "Reverse", "Potential contaminant"] + data_columns]

    panda_helper = pd.concat([panda_helper,
                              pd.DataFrame({"dataset": [dataset] * len(sample_names),
                                            "sample": sample_names})])


    # df = df.rename(columns={'oldName1': 'newName1', 'oldName2': 'newName2'})
print(".........................................")
print(" > Export Sample Meta Helper CSV to 'sample_info_out.csv' ...")
panda_helper.to_csv("/home/andreaslindner/Projects/MitoCube/ImmunoCube_Data/Raw_Import/sample_info_out.csv", index=False, sep="\t")


# ['Protein IDs', 'Majority protein IDs', 'Peptide counts (all)', 'Peptide counts (razor+unique)', 'Peptide counts (unique)',
# 'Protein names', 'Gene names', 'Fasta headers', 'Number of proteins', 'Peptides', 'Razor + unique peptides', 'Unique peptides',
# 'Peptides ku_SA_LPS_01', 'Peptides Ku_SA_LPS_02', 'Peptides Ku_SA_LPS_03', 'Peptides ku_SA_LPSBFA_01', 'Peptides Ku_SA_LPSBFA_02',
# 'Peptides Ku_SA_LPSBFA_03', 'Peptides ku_SA_unstim_01', 'Peptides Ku_SA_unstim_02', 'Peptides Ku_SA_unstim_03',
# 'Peptides Ku_SA_unstimBFA_01', 'Peptides Ku_SA_unstimBFA_02', 'Peptides Ku_SA_unstimBFA_03', 'Razor + unique peptides ku_SA_LPS_01',
# 'Razor + unique peptides Ku_SA_LPS_02', 'Razor + unique peptides Ku_SA_LPS_03', 'Razor + unique peptides ku_SA_LPSBFA_01',
# 'Razor + unique peptides Ku_SA_LPSBFA_02', 'Razor + unique peptides Ku_SA_LPSBFA_03', 'Razor + unique peptides ku_SA_unstim_01',
# 'Razor + unique peptides Ku_SA_unstim_02', 'Razor + unique peptides Ku_SA_unstim_03', 'Razor + unique peptides Ku_SA_unstimBFA_01',
# 'Razor + unique peptides Ku_SA_unstimBFA_02', 'Razor + unique peptides Ku_SA_unstimBFA_03', 'Unique peptides ku_SA_LPS_01',
# 'Unique peptides Ku_SA_LPS_02', 'Unique peptides Ku_SA_LPS_03', 'Unique peptides ku_SA_LPSBFA_01', 'Unique peptides Ku_SA_LPSBFA_02',
# 'Unique peptides Ku_SA_LPSBFA_03', 'Unique peptides ku_SA_unstim_01', 'Unique peptides Ku_SA_unstim_02', 'Unique peptides Ku_SA_unstim_03',
# 'Unique peptides Ku_SA_unstimBFA_01', 'Unique peptides Ku_SA_unstimBFA_02', 'Unique peptides Ku_SA_unstimBFA_03', 'Sequence coverage [%]',
# 'Unique + razor sequence coverage [%]', 'Unique sequence coverage [%]',
# 'Mol. weight [kDa]', 'Sequence length', 'Sequence lengths', 'Q-value', 'Score',
# 'Identification type ku_SA_LPS_01', 'Identification type Ku_SA_LPS_02', 'Identification type Ku_SA_LPS_03',
# 'Identification type ku_SA_LPSBFA_01', 'Identification type Ku_SA_LPSBFA_02', 'Identification type Ku_SA_LPSBFA_03',
# 'Identification type ku_SA_unstim_01', 'Identification type Ku_SA_unstim_02', 'Identification type Ku_SA_unstim_03',
# 'Identification type Ku_SA_unstimBFA_01', 'Identification type Ku_SA_unstimBFA_02', 'Identification type Ku_SA_unstimBFA_03',
# 'Sequence coverage ku_SA_LPS_01 [%]', 'Sequence coverage Ku_SA_LPS_02 [%]', 'Sequence coverage Ku_SA_LPS_03 [%]',
# 'Sequence coverage ku_SA_LPSBFA_01 [%]', 'Sequence coverage Ku_SA_LPSBFA_02 [%]', 'Sequence coverage Ku_SA_LPSBFA_03 [%]',
# 'Sequence coverage ku_SA_unstim_01 [%]', 'Sequence coverage Ku_SA_unstim_02 [%]', 'Sequence coverage Ku_SA_unstim_03 [%]',
# 'Sequence coverage Ku_SA_unstimBFA_01 [%]', 'Sequence coverage Ku_SA_unstimBFA_02 [%]', 'Sequence coverage Ku_SA_unstimBFA_03 [%]',
# 'Intensity',
# 'Intensity ku_SA_LPS_01', 'Intensity Ku_SA_LPS_02', 'Intensity Ku_SA_LPS_03', 'Intensity ku_SA_LPSBFA_01',
# 'Intensity Ku_SA_LPSBFA_02', 'Intensity Ku_SA_LPSBFA_03', 'Intensity ku_SA_unstim_01', 'Intensity Ku_SA_unstim_02',
# 'Intensity Ku_SA_unstim_03', 'Intensity Ku_SA_unstimBFA_01', 'Intensity Ku_SA_unstimBFA_02', 'Intensity Ku_SA_unstimBFA_03',
# 'MS/MS count', 'Peptide sequences', 'Only identified by site', 'Reverse', 'Potential contaminant', 'id', 'Peptide IDs',
# 'Peptide is razor', 'Mod. peptide IDs', 'Evidence IDs', 'MS/MS IDs', 'Best MS/MS', 'Oxidation (M) site IDs',
# 'Oxidation (M) site positions', 'Taxonomy IDs', 'Taxonomy names']

print("\n\n")
print("=========================================")
print("Re-import Meta Information and Import Dataset if not already there")
print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
print("> Import 'sample_info_in.csv' ...")
sample_info_table = pd.read_csv("/home/andreaslindner/Projects/MitoCube/ImmunoCube_Data/Raw_Import/sample_info_in.csv", sep="\t")
sample_info_table.set_index(["dataset", "sample"], inplace = True)

# sample_info_table.columns
print(" (i) Column 'do_not_import'")
print(sample_info_table["do_not_import"].unique())
print(" (i) Column 'replicate'")
print(sample_info_table["replicate"].unique())
print(" (i) Column 'knockout'")
print(sample_info_table["knockout"].unique())
print(" (i) Column 'timepoint'")
print(sample_info_table["timepoint"].unique())
print(" (i) Column 'treatment'")
print(sample_info_table["treatment"].unique())
print(" (i) Column 'instrument'")
print(sample_info_table["instrument"].unique())
print(".........................................")
print(" > prepare missing Instruments")
db_instruments = dlib.ABCInstrument.get_class()

if not db_instruments.does_exist_with_label(label="obscurus"):
    obscurus = psql.PostgreSQLInstrument(label="obscurus", name="Obscurus", location="Munich, DE",
                                         description = "Obscurus, MS", base64_image = None)
    obscurus.write_to_db()
else:
    obscurus = db_instruments.objectify_with_label(label="obscurus")
print(".........................................")
print(" > prepare missing Attributes")
db_attributes: Type[dlib.ABCAttribute] = dlib.ABCAttribute.get_class()
attributes = db_attributes.get_all_attributes()
attributes_tags = {item.get_tag(): db_id for db_id, item in attributes.items()}

for tag, item in attribute_info.items():
    if tag not in attributes_tags.keys():
        print(" > Adding Attribute '{}' ...".format(tag))
        att = psql.PostgreSQLAttribute(parent_attribute = None,
                                       tag = tag,
                                       text = item["text"],
                                       priority = item["priority"],
                                       db_id = None,
                                       allow_as_filter = True, allow_for_dataset = True,
                                       allow_for_genotype = False, allow_for_performance = False,
                                       allow_for_sample = True, allow_trait_values = True, required_for_dataset_state = dlib.DatasetState.ACTIVE)
        att.write_to_db()
print(".........................................")
print(" > prepare missing Traits")
attributes = db_attributes.get_all_attributes()
attributes_tags = {item.get_tag(): db_id for db_id, item in attributes.items()}

db_traits: Type[dlib.ABCTrait] = dlib.ABCTrait.get_class()
traits = db_traits.get_all_traits(attributes = attributes)
trait_tags = {item.get_full_tag(): db_id for db_id, item in traits.items()}

for full_tag, item in trait_info.items():
    if full_tag not in trait_tags.keys():
        trait = db_traits(parent_attribute = attributes[attributes_tags[item["attribute_tag"]]],
                          tag = item["tag"],
                          text = item["text"],
                          keyword = item["keyword"],
                          description = item["description"],
                          db_id = None)
        trait.write_to_db()
print(".........................................")
attributes = db_attributes.get_all_attributes()
attributes_tags = {item.get_tag(): db_id for db_id, item in attributes.items()}

db_traits: Type[dlib.ABCTrait] = dlib.ABCTrait.get_class()
traits = db_traits.get_all_traits(attributes = attributes)
trait_tags = {item.get_full_tag(): db_id for db_id, item in traits.items()}

print("=========================================")

print("\n\n")
print("=========================================")
print("Import Datasets with all associated information")
print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")

db_trait_values: Type[dlib.ABCTraitValue] = dlib.ABCTraitValue.get_class()

db_dataset : Type[dlib.ABCDataset] = dlib.ABCDataset.get_class()

for dataset_tag, info in meta_info.items():
    if db_dataset.does_exist_with_label(dataset_tag):
        print(" ! Dataset with '{}' label already exists. Skipping Import!".format(dataset_tag))
        continue

    print(" > Creating dataset '{}' ...".format(dataset_tag))
    dataset = psql.PostgreSQLDataset(external_id=dataset_tag,
                                     data=None, parent_project=None,
                                     instrument=obscurus,
                                     created_on=info["created_on"],
                                     state=dlib.DatasetState.ACTIVE,
                                     title=info["title"],
                                     owner_user=felix, owner_group=None,
                                     contact_email="felix.meissner@uni-bonn.de",
                                     metatexts=None,
                                     urls=None,
                                     trait_values=None)
    dataset.write_to_db(write_datatable = False)
    print(" > Created dataset '{}' with database id '{}'.".format(dataset_tag, dataset.get_internal_id()))

    if info["species"] == "mouse":
        trait_value = psql.PostgreSQLTraitValue(trait=traits[trait_tags["att_organism:mouse"]], value=None,
                                                unit=None)
        trait_value.add_to_dataset_id(dataset_id=dataset.get_internal_id())

    elif info["species"] == "human":
        trait_value = psql.PostgreSQLTraitValue(trait=traits[trait_tags["att_organism:human"]], value=None,
                                                unit=None)
        trait_value.add_to_dataset_id(dataset_id=dataset.get_internal_id())

    file = "/home/andreaslindner/Projects/MitoCube/ImmunoCube_Data/Raw_Import/" + dataset_tag + "/proteinGroups.txt"
    print("> Importing file '{}' ...".format(file))
    df = pd.read_csv(file, sep="\t")

    data_columns = list(filter(re_column_search.match, list(df.columns)))
    df = df[["Protein IDs", "Reverse", "Potential contaminant"] + data_columns]

    df = df[df["Reverse"] != "+"]  # df["Reverse"].unique()
    df = df[df["Potential contaminant"] != "+"]  # df["Potential contaminant"].unique()

    df = df[["Protein IDs"] + data_columns]
    df.rename(columns={"Protein IDs": "Key"}, inplace = True)

    sample_names = [re_column_search.search(str_column).group(1) for str_column in data_columns]
    df.rename(columns={data_columns[ix]: sample_names[ix] for ix in range(len(data_columns))}, inplace = True)
    data_columns = sample_names

    data_columns_to_keep = data_columns

    replicates_samples: Dict[str, str] = {}
    trait_values_samples: Dict[str, List[dlib.ABCTraitValue]] = {}

    for sample_name in info["samples"]:
        sample_info = sample_info_table.loc[(dataset_tag, sample_name)]

        if sample_info["do_not_import"] and sample_info["do_not_import"] == "do_not_import":
            print(" (!) Ignoring sample '{}' of '{}'. Skip Import!".format(sample_name, dataset_tag))
            data_columns_to_keep.remove(sample_name)
        else:
            print(" (i) Importing sample '{}' of '{}' ...".format(sample_name, dataset_tag))
            trait_values_samples[sample_name] = []

            if sample_info["replicate"] and pd.notna(sample_info["replicate"]):
                if isinstance(sample_info["replicate"], numbers.Number):
                    replicates_samples[sample_name] = str(int(sample_info["replicate"]))
                else:
                    replicates_samples[sample_name] = sample_info["replicate"]

            if sample_info["knockout"] and pd.notna(sample_info["knockout"]):
                trait_values_samples[sample_name].append(psql.PostgreSQLTraitValue(trait=traits[trait_tags["att_knockout_stat:" + str(sample_info["knockout"])]],
                                                                                   value=None, unit=None))
            if sample_info["timepoint"] and pd.notna(sample_info["timepoint"]):
                trait_values_samples[sample_name].append(psql.PostgreSQLTraitValue(trait=traits[trait_tags["att_timepoint:" + str(sample_info["timepoint"])]],
                                                                                   value=None, unit=None))
            if sample_info["treatment"] and pd.notna(sample_info["treatment"]):
                trait_values_samples[sample_name].append(psql.PostgreSQLTraitValue(trait=traits[trait_tags["att_treatment:" + str(sample_info["treatment"])]],
                                                                                   value=None, unit=None))
            if sample_info["other"] and pd.notna(sample_info["other"]):
                trait_values_samples[sample_name].append(psql.PostgreSQLTraitValue(trait=traits[trait_tags["att_other:" + str(sample_info["other"])]],
                                                                                   value=None, unit=None))


    if len(data_columns_to_keep) > 0:
        df = df[["Key"] + data_columns_to_keep]
        df.set_index("Key", inplace=True)

        df[data_columns_to_keep] = df[data_columns_to_keep].apply(np.log2, )
        df.replace([np.inf, -np.inf], np.nan, inplace=True)

        data_table = psql.PostgreSQLDataTable(parent_dataset = dataset,
                                              data_wide = df,
                                              replicates_samples = replicates_samples,
                                              batches_samples = None,
                                              trait_values_samples = trait_values_samples)
        data_table.write_to_db()
    else:
        print("Dataset '{}' has no samples to import!".format(dataset_tag))


print(".........................................")
print("=========================================")

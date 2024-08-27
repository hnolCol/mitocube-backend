from __future__ import annotations

from abc import abstractmethod
from typing import List
from threading import Lock
import os
import pandas as pd

from config import get_system_settings
from lib.designpatterns import SingletonABCMeta
import lib.data as dlib


class PandaFeatureDatabase(dlib.ABCFeatureDatabase):

    def __init__(self):
        self._lock = Lock()

        self._feature_paths : List[str] = []
        self._cached_features : pd.DataFrame | None = None
        self._cached_info : pd.DataFrame | None = None  # todo: implement the read function and row merge

    def read(self):
        print(" > Panda read(...)")

        CONF = get_system_settings()

        dir_root = CONF.path_features

        if not os.path.exists(dir_root):
            raise FileNotFoundError(f"Invalid feature database path {dir_root}.")

        # question: cCheck if the following is true
        # According to https://peps.python.org/pep-0343/ lock is guaranteed to be released when the block is left
        with self._lock:
            self._feature_paths = []
            self._cached_features = None
            self._cached_info = None

            for path in os.scandir(dir_root):
                if path.is_dir():
                    featureFile = os.path.join(dir_root, path.name, "data.txt")
                    infoFile = os.path.join(dir_root, path.name, "info.txt")
                    mappingFile = os.path.join(dir_root, path.name, "mappings.txt")

                    if not os.path.exists(mappingFile):
                        raise FileNotFoundError(f"Missing mapping file {mappingFile}.")

                    if not os.path.exists(featureFile):
                        raise FileNotFoundError(f"Missing feature database file {featureFile}.")

                    if not os.path.exists(mappingFile):
                        raise FileNotFoundError(f"Missing mapping file {mappingFile}.")

                    try:
                        mappings = pd.read_csv(mappingFile, sep="\t")
                    except Exception as error:
                        raise Exception(f"Unable to import {mappingFile}: {error}")

                    try:
                        info = pd.read_csv(infoFile, sep="\t", header = None, index_col=0)
                    except Exception as error:
                        raise Exception(f"Unable to import {infoFile}: {error}")

                    try:
                        features = pd.read_csv(featureFile, sep="\t")
                    except Exception as error:
                        raise Exception(f"Unable to import {featureFile}: {error}")

                    mappings.set_index("map", inplace=True)

                    # FixMe: is there a smarter / more performance way to rename / sort columns?
                    features = pd.DataFrame(data = features.loc[:, mappings.loc[:, "from"].values].values,
                                            columns = mappings.index.values)

                    features["proteom_id"] = info.loc["proteom_id"].values[0]

                    # ToDo: Cleaner solution for below? issue with multiindex with merge (does not preserve indices), hence keep a copy column and restore if needed
                    features["ix_proteom_id"] = features["proteom_id"]
                    features["ix_organism_id"] = features["organism_id"]
                    features["ix_key"] = features["key"]
                    features["ix_entry"] = features["entry"]
                    features.set_index(["ix_proteom_id", "ix_organism_id", "ix_key", "ix_entry"], drop=True, inplace=True)

                    if self._cached_features:
                        self._cached_features = pd.concat([self._cached_features, features])
                    else:
                        self._cached_features = features

    def reset(self):
        with self._lock:
            self._feature_paths = []
            self._cached_features = {}
            self._cached_info = None

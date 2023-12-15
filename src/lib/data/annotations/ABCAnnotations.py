from __future__ import annotations

import os
from abc import ABC, abstractmethod
from threading import Lock

from collections import OrderedDict
from typing import Any, Dict, List
from threading import Lock

import datetime
import pandas as pd
# numpy as np

from lib.DesignPatterns import SingletonABCMeta

from config.settings.annotationsettings import get_annotation_settings
from config.settings.general import get_general_settings 
from config.settings.db import get_db_settings


ANNOTATION_SETTINGS = get_annotation_settings()
GENERAL_SETTINGS = get_general_settings() 
DB_SETTINGS = get_db_settings()


class Annotation(ABC):

    @abstractmethod
    def contains(self, feature_key: str) -> bool:
        """Returns true if the defined feature (key) has a stored annotation. Otherwise, false."""
        pass

    @abstractmethod
    def getAnnotations(self, feature_key: str) -> List[str]:  # ToDo: make a function that requests annotations of multiple keys
        """Returns a list of annotations defined for the feature (key). May throws a KeyError if feature is not in the list."""
        pass

    def getDescriptionalTag(self) -> str:
        """Returns a descriptional tag including the class name and SpeciesID."""
        return "%s_%s_%s" % (self.__class__.__name__,
                             self.getSpeciesID(),
                             self.getProteomeID())

    @abstractmethod
    def getSpeciesID(self) -> str:
        """Returns the species ID of the annotations."""
        pass

    @abstractmethod
    def getProteomeID(self) -> str:
        """Returns the Proteome ID of the annotations."""
        pass

    @abstractmethod
    def length(self) -> int:
        """Returns the number of features (keys) with deposited annotations."""
        pass


class SequenceAnnotation(Annotation):
    """"""
    def __init__(self, species_id : str, proteome_id : str,data : pd.DataFrame):
        self._species_id = species_id
        self._proteome_id = proteome_id
        self._data = data

        self._data.set_index("key", inplace=True)

    def contains(self, feature_key: str) -> bool:
        """Returns true if the defined feature (key) has a stored annotation. Otherwise, false."""
        return feature_key in self._data.index

    def getAnnotations(self, feature_key: str) -> List[str]:
        """Returns a list of annotations defined for the feature (key). May throws a KeyError if feature is not in the list."""
        return self._data.loc[feature_key, ].tolist()

    def getSpeciesID(self) -> str:
        """Returns the species ID of the annotations."""
        return self._species_id

    def getProteomeID(self) -> str:
        """Returns the Proteome ID of the annotations."""
        return self._proteome_id

    def length(self) -> int:
        """Returns the number of features (keys) with deposited annotations."""
        return len(self._data)


class KeywordAnnotation(Annotation):
    """"""

    def __init__(self, species_id : str, proteome_id : str, data : pd.DataFrame):
        self._species_id = species_id
        self._proteome_id = proteome_id

        self._keywords_data = {}
        self._keyword_ids_data = {}
        # self._keywords_data_reverse = {}  # ToDo: is there a need for reverse search? keywords to proteins

        for index, row in data.iterrows():
            if not pd.isnull(row["keywords"]):
                keywords = [item.lstrip() for item in row["keywords"].split(";")]
                keywords_ids = [item.lstrip() for item in row["keywords_id"].split(";")]

                self._keywords_data[row["key"]] = keywords
                self._keyword_ids_data[row["key"]] = keywords_ids

    def contains(self, feature_key: str) -> bool:
        """Returns true if the defined feature (key) has a stored annotation. Otherwise, false."""
        return feature_key in self._keywords_data.keys()

    def getAnnotations(self, feature_key: str) -> Any:
        """Returns a list of annotations defined for the feature (key). May throws a KeyError if feature is not in the list."""
        return self._keywords_data[feature_key]

    def getSpeciesID(self) -> str:
        """Returns the species ID of the annotations."""
        return self._species_id

    def getProteomeID(self) -> str:
        """Returns the Proteome ID of the annotations."""
        return self._proteome_id

    def length(self) -> int:
        """Returns the number of features (keys) with deposited annotations."""
        return len(self._keywords_data)


class GOAnnotation(Annotation):
    """"""

    def __init__(self, species_id : str, proteome_id : str, data : pd.DataFrame):
        self._species_id = species_id
        self._proteome_id = proteome_id

        self._go_data = {}
        self._go_ids_data = {}
        # self._go_data_Reverse = {}  # ToDo: is there a need for reverse search? go term to proteins

        for index, row in data.iterrows():
            # go
            if not pd.isnull(row["go"]):
                go = [item.lstrip() for item in row["go"].split(";")]
                go_ids = [item.lstrip() for item in row["go_ids"].split(";")]

                self._go_data[row["key"]] = go
                self._go_ids_data[row["key"]] = go_ids

    def contains(self, feature_key: str) -> bool:
        """Returns true if the defined feature (key) has a stored annotation. Otherwise, false."""
        return feature_key in self._go_data.keys()

    def getAnnotations(self, feature_key: str) -> Any:
        """Returns a list of annotations defined for the feature (key). May throws a KeyError if feature is not in the list."""
        return self._go_data[feature_key]

    def getSpeciesID(self) -> str:
        """Returns the species ID of the annotations."""
        return self._species_id

    def getProteomeID(self) -> str:
        """Returns the Proteome ID of the annotations."""
        return self._proteome_id

    def length(self) -> int:
        """Returns the number of features (keys) with deposited annotations."""
        return len(self._go_data)


class AnnotationDatabase(metaclass=SingletonABCMeta):
    def __init__(self):
        """Singleton Constructor"""
        self._lock = Lock()  # Synchronization primitive to make it multi-threading safe

        self._cached_annotations = {}  # Dict[str, List[Annotations]] of annotations
        self._timestamp_updated = None

    def clearCachedAnnotations(self):
        """
        Clears the cached of (memory) stored annotations.
        """
        self._cached_annotations.clear()
        self._timestamp_updated = None

    def update(self):
        """"""
        self._lock.acquire()
        self._cached_annotations = PandaAnnotateFactory.importAnnotations()
        self._timestamp_updated = datetime.datetime.now()
        self._lock.release()

    def getUpdatedOn(self) -> datetime.datetime:
        """"""
        return self._timestamp_updated

    def hasAnnotations(self, feature_key: str, proteome_id: str = None) -> bool:
        """Returns true if there is any annotation."""
        if proteome_id is None:
            for key, annotationSets in self._cached_annotations.items():
                for annotationSet in annotationSets:
                    if annotationSet.contains(feature_key):
                        return True
        else:
            for annotationSet in self._cached_annotations[proteome_id]:
                if annotationSet.contains(feature_key):
                    return True

        return False

    def getAnnotations(self, feature_key: str, proteome_id: str = None) -> Dict[str, List[str]]:
        """Returns a dictionary for all annotation founds for a feature with specified keys, or an empty Dict if nothing was found."""
        identifiedAnnotations = {}

        if proteome_id is None:
            for key, annotationSets in self._cached_annotations.items():
                for annotationSet in annotationSets:
                    if annotationSet.contains(feature_key):
                        identifiedAnnotations[annotationSet.getDescriptionalTag()] = annotationSet.getAnnotations(feature_key)
        else:
            for annotationSet in self._cached_annotations[proteome_id]:
                if annotationSet.contains(feature_key):
                    identifiedAnnotations[annotationSet.getDescriptionalTag()] = annotationSet.getAnnotations(feature_key)

        return identifiedAnnotations

    # ToDo: getAnnotation feature_key List[str]


class FeatureDatabase(metaclass=SingletonABCMeta):
    """
    Singleton class/object that imports and holds annotations of features for the database.

    Return an object by using db_features = FeatureDatabase() and request the feature list by eiter db_features.get() for all features or db_features.get(keys=["A0A075B6G3_HUMAN", "CF047_MOUSE"].
    """

    @abstractmethod
    def find(self, values : List[str], proteome_id: str = None, columns : List[str] = None) -> pd.DataFrame:
        """Finds List[str] values in the List[str] columns defined. Only the values "entry", "proteins" and "genes" are allowed in columns. Columns "proteins" and "genes" are used by default."""
        pass

    @abstractmethod
    def get(self, keys : List[str] = None, proteome_id: str = None, ignoreMissing = False) -> pd.DataFrame:
        """Returns a Pandas DataFrame of all Feature Settings if no keys are defined, or items matching the keys. May throws KeyError Exception if key is not in the annotation table. Set ignoreMissing to true to return only matching rows. Returns multiple rows if key is not unique."""
        pass

    @abstractmethod
    def reset(self):
        """Empties the annotation table."""
        pass

    @abstractmethod
    def update(self):
        """Imports the annotation tables defined in the configurations. Keeps only first entry if duplicate rows are imported."""
        pass


class PandaAnnotateFactory:
    @staticmethod
    def importAnnotations() -> Dict[str, list[Annotation]]:
        """Imports and returns (as List) the annotation tables defined in the configurations and found in the defined directory. """
        # self._lock.acquire()
        annotationsCollection = {}  # Dict[str, List[Annotations]] of annotations

        dir_root = ANNOTATION_SETTINGS.path_annotations

        if not os.path.exists(dir_root):
            # self._lock.release()
            raise FileNotFoundError(f"Invalid annotation database path {dir_root}.")

        for item in os.scandir(dir_root):
            if item.is_dir():
                annotationFile = "%s/%s/%s" % (dir_root, item.name, ANNOTATION_SETTINGS.file_annotations)
                mappingFile = "%s/%s/%s" % (dir_root, item.name, ANNOTATION_SETTINGS.file_annotations_column_mappings)
                infoFile = "%s/%s/%s" % (dir_root, item.name, ANNOTATION_SETTINGS.info_annotations)

                if not os.path.exists(annotationFile):
                    # self._lock.release()
                    raise FileNotFoundError(f"Missing annotation database file {annotationFile}.")  # ToDo: Change to a Warning?

                try:
                    in_annotations = pd.read_csv(annotationFile, sep = ANNOTATION_SETTINGS.seperator_annotations)
                except Exception as error:
                    # self._lock.release()
                    raise Exception(f"Unable to import {annotationFile}: {error}")

                if not os.path.exists(mappingFile):
                    # self._lock.release()
                    raise FileNotFoundError(f"Missing mapping file {mappingFile}.")

                try:
                    in_mappings = pd.read_csv(mappingFile, sep = ANNOTATION_SETTINGS.seperator_annotations)
                except Exception as error:
                    # self._lock.release()
                    raise Exception(f"Unable to import {mappingFile}: {error}")

                in_mappings.set_index("map", inplace=True)

                if not os.path.exists(infoFile):
                    # self._lock.release()
                    raise FileNotFoundError(f"Missing info file {infoFile}.")

                try:
                    in_info = pd.read_csv(infoFile, sep = ANNOTATION_SETTINGS.seperator_annotations)
                except Exception as error:
                    # self._lock.release()
                    raise Exception(f"Unable to import {infoFile}: {error}")

                in_info.set_index("var", inplace=True)

                annotationsDict = OrderedDict()

                for index, row in in_mappings.iterrows():
                    annotationsDict[index] = in_annotations.loc[:, in_mappings.loc[index][0]]

                in_annotations = pd.DataFrame(annotationsDict, columns=pd.Series(annotationsDict.keys()))

                str_proteome_id = in_info.loc["proteome_id"][0]
                if str_proteome_id not in annotationsCollection.keys():
                    # There is no entry for the proteome_id yet, create an empty List
                    annotationsCollection[str_proteome_id] = []

                if in_info.loc["class"][0] == "SequenceAnnotation":
                    annotationsCollection[str_proteome_id].append(SequenceAnnotation(species_id=in_info.loc["species_id"][0],
                                                                                     proteome_id=str_proteome_id,
                                                                                     data=in_annotations))
                elif in_info.loc["class"][0] == "GoKeywordAnnotation":
                    annotationsCollection[str_proteome_id].append(KeywordAnnotation(species_id=in_info.loc["species_id"][0],
                                                                                    proteome_id=str_proteome_id,
                                                                                    data=in_annotations))
                    annotationsCollection[str_proteome_id].append(GOAnnotation(species_id=in_info.loc["species_id"][0],
                                                                               proteome_id=str_proteome_id,
                                                                               data=in_annotations))
                elif in_info.loc["class"][0] == "KeywordAnnotation":
                    annotationsCollection[str_proteome_id].append(KeywordAnnotation(species_id=in_info.loc["species_id"][0],
                                                                                    proteome_id=str_proteome_id,
                                                                                    data=in_annotations))
                elif in_info.loc["class"][0] == "GOAnnotation":
                    annotationsCollection[str_proteome_id].append(GOAnnotation(species_id=in_info.loc["species_id"][0],
                                                                               proteome_id=str_proteome_id,
                                                                               data=in_annotations))
                else:
                    raise Exception("Invalid Annotation (%s) configuration. Only 'SequenceAnnotation' and 'GOAnnotation' are supported." % (in_infos.loc["class"][0]))

        return annotationsCollection
        # self._lock.release()


class PandaFeatureDatabase(FeatureDatabase):
    """"""

    def __init__(self):  # ToDo: Check DataType Date
        """Singleton Constructor"""
        self._lock = Lock()  # Synchronization primitive to make it multi-threading safe

        self._featureFiles = []
        self._cached_features = {}  # Dict[str (proteome_id), pd.DataFrame(index=[], columns=["entry", "key", "proteins", "genes", "organism", "aa_length"])]

    def find(self, values : List[str], proteome_id: str = None, columns : List[str] = None) -> pd.DataFrame:
        """Finds List[str] values in the List[str] columns defined. Only the values "entry", "proteins" and "genes" are allowed in columns. Columns "proteins" and "genes" are used by default."""

        if columns is None:
            strs_columns = ["proteins", "genes"]
        else:
            strs_columns = [value for value in columns if value in ["entry", "proteins", "genes"]]

            if not strs_columns:
                raise Exception("Columns provided are not allowed. Please use entry, proteins or genes only.")

        results_or = [False] * self._cached_features.shape[0]

        for str_term in values:
            for str_column in strs_columns:
                results_or = [a or b for a,b in zip(results_or,
                                                    self._cached_features[str_column].str.contains(str_term))]

        return self._cached_features.loc[results_or]

    def get(self, keys : List[str] = None, proteome_id: str = None, ignoreMissing = False) -> pd.DataFrame:
        """Returns a Pandas DataFrame of all AnnotationSettings if no keys are defined, or items matching the keys. May throws KeyError Exception if key is not in the annotation table. Set ignoreMissing to true to return only matching rows. Returns multiple rows if key is not unique. Will throw a KeyError exception for the wrong proteome_id."""

        if proteome_id is None:
            collected_features = pd.DataFrame(index=[],
                                              columns=["entry", "key", "proteins", "genes", "organism", "organism_id",
                                                       "aa_length", "mass", "proteome_id"])
            if keys is None:
                for proteome_id_loop, item in self._cached_features.items():
                    item = self._cached_features[proteome_id_loop].copy()
                    item["proteome_id"] = proteome_id_loop
                    collected_features = pd.concat([collected_features, item], axis=0)
            else:
                for proteome_id_loop, item in self._cached_features.items():
                    keys_to_use = keys
                    if ignoreMissing:
                        keys_to_use = self._cached_features[proteome_id_loop].index.intersection(keys_to_use)

                    item = self._cached_features[proteome_id_loop].loc[keys_to_use].copy()
                    item["proteome_id"] = proteome_id_loop
                    collected_features = pd.concat([collected_features, item], axis=0)

            return collected_features
        else:
            if keys is None:
                return self._cached_features[proteome_id]
            else:
                if not ignoreMissing:
                    return self._cached_features[proteome_id].loc[keys]
                else:
                    return self._cached_features[proteome_id].loc[self._cached_features[proteome_id].index.intersection(keys)]

    def getAnnotationFiles(self) -> List[str]:
        """Returns a List[str] of imported annotation files."""
        return self._featureFiles

    def reset(self):
        """Reset function that empties the annotation table."""
        self._lock.acquire()
        self._featureFiles = []
        self._cached_features = {}
        self._lock.release()

    def update(self):
        """Imports the annotation tables defined in the configurations. Keeps only first entry if duplicate rows are imported."""
        self._lock.acquire()
        self._featureFiles = []
        self._cached_features = {}

        dir_root = ANNOTATION_SETTINGS.path_features

        if not os.path.exists(dir_root):
            self._lock.release()
            raise FileNotFoundError(f"Invalid feature database path {dir_root}.")

        for item in os.scandir(dir_root):
            if item.is_dir():
                featureFile = "%s/%s/%s" % (dir_root, item.name, ANNOTATION_SETTINGS.file_features)
                mappingFile = "%s/%s/%s" % (dir_root, item.name, ANNOTATION_SETTINGS.file_features_column_mappings)

                if not os.path.exists(featureFile):
                    self._lock.release()
                    raise FileNotFoundError(f"Missing feature database file {featureFile}.")  # ToDo: Change to a Warning?

                try:
                    features = pd.read_csv(featureFile, sep = ANNOTATION_SETTINGS.seperator_features)
                except Exception as error:
                    self._lock.release()
                    raise Exception(f"Unable to import {featureFile}: {error}")

                if not os.path.exists(mappingFile):
                    self._lock.release()
                    raise FileNotFoundError(f"Missing mapping file {mappingFile}.")

                try:
                    mappings = pd.read_csv(mappingFile, sep = ANNOTATION_SETTINGS.seperator_features)
                except Exception as error:
                    self._lock.release()
                    raise Exception(f"Unable to import {mappingFile}: {error}")

                mappings.set_index("map", inplace=True)

                features = pd.concat([features.loc[:, mappings.loc["entry"][0]],
                                      features.loc[:, mappings.loc["key"][0]],
                                      features.loc[:, mappings.loc["proteins"][0]],
                                      features.loc[:, mappings.loc["genes"][0]],
                                      features.loc[:, mappings.loc["organism"][0]],
                                      features.loc[:, mappings.loc["organism_id"][0]],
                                      features.loc[:, mappings.loc["aa_length"][0]],
                                      features.loc[:, mappings.loc["mass"][0]]],
                                     axis=1)

                features.rename(columns={mappings.loc["entry"][0]: "entry",
                                         mappings.loc["key"][0]: "key",
                                         mappings.loc["proteins"][0]: "proteins",
                                         mappings.loc["genes"][0]: "genes",
                                         mappings.loc["organism"][0]: "organism",
                                         mappings.loc["organism_id"][0]: "organism_id",
                                         mappings.loc["aa_length"][0]: "aa_length",
                                         mappings.loc["mass"][0]: "mass"},
                                inplace=True)

                # pd.DataFrame(index=[],# columns=["entry", "key", "proteins", "genes", "organism", "organism_id", "aa_length", "mass"])
                # self._cached_features = pd.concat([self._cached_features, features], axis=0)
                self._cached_features[item.name] = features
                self._cached_features[item.name].fillna(value="", inplace=True)
                self._cached_features[item.name].drop_duplicates(keep="first", inplace=True)
                self._cached_features[item.name].set_index("key", inplace=True)

                self._featureFiles.append(featureFile)

        self._lock.release()

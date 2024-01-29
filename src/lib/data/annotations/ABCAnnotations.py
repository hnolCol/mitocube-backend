from __future__ import annotations
import os
from abc import ABC, abstractmethod
from threading import Lock

from collections import OrderedDict
from typing import Any, Dict, List, Literal, Optional
from threading import Lock

import datetime
import pandas as pd
import numpy as np 
# numpy as np

from lib.DesignPatterns import SingletonABCMeta

from config.settings.annotationsettings import get_annotation_settings
from config.settings.general import get_general_settings 
from config.settings.db import get_db_settings

from services.regex import build_regex_for_search


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
        
    def getAnnotationType(self) -> str:
        """Returns the annotations class name"""
        return self.__class__.__name__

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
    def __init__(self, species_id : str, proteome_id : str, data : pd.DataFrame):
        self._species_id = species_id
        self._proteome_id = proteome_id
        self._data = data

        self._data.set_index("key", inplace=True)

    def contains(self, feature_key: str) -> bool:
        """Returns true if the defined feature (key) has a stored annotation. Otherwise, false."""
        return feature_key in self._data.index

    def getAnnotations(self, feature_key: str) -> List[str]:
        """
        Returns a list of annotations defined for the feature (key).
        
        Parameters
        ----------
        feature_key : str 
            The feature_key to get the annotation for. 
        
        Returns
        -------
        List[str]
            The sequence in a list. 
            
        Raises
        ------
        KeyError 
            If feature is not in the list."""
            
        return [self._data.loc[feature_key,"sequence"]] #add sequence, otherwise would return Entry Sequence as list.. List since it should add the other annotation outputs? 

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

        no_nan_data = data.dropna(subset=["keywords"]).set_index("key") #remove  nan and set key as index 
        keywords_splits = no_nan_data.loc[:,"keywords"].str.split(";") #danger! ";"
        keywords_ids_splits = no_nan_data.loc[:,"keywords_id"].str.split(";") #danger! ";" used

        self._keywords_data = keywords_splits.to_dict()
        self._keyword_ids_data = keywords_ids_splits.to_dict()
        # see GOAnnotation for speed comparison. 
        # for index, row in data.iterrows():
        #     if not pd.isnull(row["keywords"]):
        #         keywords = [item.lstrip() for item in row["keywords"].split(";")]
        #         keywords_ids = [item.lstrip() for item in row["keywords_id"].split(";")]

        #         self._keywords_data[row["key"]] = keywords
        #         self._keyword_ids_data[row["key"]] = keywords_ids

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
    """
    Parameters
    ----------
    species_id : str
        Species id 
    proteome_id : str
        Reference proteome id 
    data : pd.DataFrame
        Annotation file loaded and mapped to expected columns. 
        TODO: check the data file if it contains the correct column names?
    """
    
    def __init__(self, species_id : str, proteome_id : str, data : pd.DataFrame):
        self._species_id = species_id
        self._proteome_id = proteome_id

        self._go_data : Dict[str,List[str]] = {}
        self._go_ids_data : Dict[str,List[str]] = {} # this is this type? 
        # self._go_data_Reverse = {}  # ToDo: is there a need for reverse search? go term to proteins #Probably useful if we implement GO enrichments 
        # general : do we need ids ? They are kinda in the name []? 
        
        #I assumed this might be faster
        #import time
        #t1 = time.time()
        # remove nan and set key as index
        no_nan_data = data.dropna(subset=["go"]).set_index("key")
        go_splits = no_nan_data.loc[:,"go"].str.split("; ") #danger! "; " used
        go_ids_splits = no_nan_data.loc[:,"go_ids"].str.split("; ") #danger! "; " used
        # one could discuss if we want to keep the data like this instead of a dict? 
        # i am not sure if this is an uniprot export issue with the "; " instead of ";" as separators? If consistent I would just split on that? The information about the GO is not present e.g. Cellular Compartment? Molecular Function
        # transform to dict 
        self._go_data = go_splits.to_dict()
        self._go_ids_data = go_ids_splits.to_dict()
        
        #print(time.time()-t1)
        #t2 = time.time()
        # for index, row in data.iterrows():
        #     # go
        #     if not pd.isnull(row["go"]):
        #         go = [item.lstrip() for item in row["go"].split(";")]
        #         go_ids = [item.lstrip() for item in row["go_ids"].split(";")]
        #         self._go_data[row["key"]] = go
        #         self._go_ids_data[row["key"]] = go_ids
        #print(time.time()-t2)
        # time results :: bit unfair due to ignore lstrip in the first method. lets talk about it
        # 0.28241801261901855
        # 3.3776321411132812 -iterrows based
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

    def getAnnotations(self, feature_key: str, proteome_id: str = None, subset : Optional[List[Literal["SequenceAnnotation","KeywordAnnotation","GOAnnotation"]]] = None) -> Dict[str, List[str]]:
        """
        Returns a dictionary for annotations found for a feature with specified key, or an empty Dict if nothing was found.
        
        Parameters
        ----------
        feature_key : str 
            The key of the feature (UniprotID)
        proteome_id : str, default None
            Reference proteome id. 
        subset : Optional[List[Literal["SequenceAnnotation","KeywordAnnotation","GOAnnotation"]]], optional, default None
            Subset the annotation database by class using the AnnotationClasses. 
            
        Returns
        -------
        Dict[str,List[str]]
            The annotations for the feature_key. If feature_key is not found, an empty dict is returned. 
            Keys present the description tag ``getDescriptionTag()`` and values are a list of annotations as string. 
        
        See also
        --------
        getDescriptionTag()
        """
        identifiedAnnotations = {}

        if proteome_id is None:
            for key, annotationSets in self._cached_annotations.items():
                for annotationSet in annotationSets:
                    if subset is not None and not annotationSet.getAnnotationType() in subset:
                        continue
                    if annotationSet.contains(feature_key):
                        identifiedAnnotations[annotationSet.getDescriptionalTag()] = annotationSet.getAnnotations(feature_key)
        else:
            for annotationSet in self._cached_annotations[proteome_id]:
                if subset is not None and not annotationSet.getAnnotationType() in subset:
                        continue
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
        """
        Imports and returns (as List) the annotation tables defined in the configurations and found in the defined directory.
        
        Raises
        ------
        Exception
            If path is not existing. 
            If the import returned an error pd.csv()
        """
        # self._lock.acquire()
        annotationsCollection = {}  # Dict[str, List[Annotations]] of annotations

        dir_root = ANNOTATION_SETTINGS.path_annotations

        if not os.path.exists(dir_root):
            # self._lock.release()
            raise FileNotFoundError(f"Invalid annotation database path {dir_root}.")

        for item in os.scandir(dir_root):
            if item.is_dir():
                annotationFile = os.path.join(dir_root, item.name, ANNOTATION_SETTINGS.file_annotations)
                mappingFile = os.path.join(dir_root, item.name, ANNOTATION_SETTINGS.file_annotations_column_mappings)
                infoFile = os.path.join(dir_root, item.name, ANNOTATION_SETTINGS.info_annotations)

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

                # annotationsDict = OrderedDict()

                # for index, row in in_mappings.iterrows():
                #     annotationsDict[index] = in_annotations.loc[:, in_mappings.loc[index][0]]
                # in_annotations = pd.DataFrame(annotationsDict, columns=pd.Series(annotationsDict.keys()))
                # I guess this is faster and easy one liner. 
                in_annotations = pd.DataFrame(data = in_annotations.loc[:,in_mappings["from"].values].values,
                                              columns = in_mappings.index.values) #not sure if setting the map values to index is required?
                
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
                    raise Exception("Invalid Annotation (%s) configuration. Only 'SequenceAnnotation' and 'GOAnnotation' are supported." % (in_info.loc["class"][0]))

        return annotationsCollection
        # self._lock.release()


class PandaFeatureDatabase(FeatureDatabase):
    """"""

    def __init__(self):  # ToDo: Check DataType Date
        """Singleton Constructor"""
        self._lock = Lock()  # Synchronization primitive to make it multi-threading safe

        self._featureFiles : List[str] = [] #list of paths? 
        self._cached_features : Dict[str,pd.DataFrame] = {}  # Dict[str (proteome_id), pd.DataFrame(index=[], columns=["entry", "key", "proteins", "genes", "organism", "aa_length"])]


    def find(self, values : List[str], proteome_id: str, columns : List[Literal["entry","proteins","genes"]] = None) -> pd.DataFrame:
        """
        Finds List[str] values in the List[str] columns defined. 
        Only the values "entry", "proteins" and "genes" are allowed in columns. Columns "proteins" and "genes" are used by default.
        
        Parameters
        ----------
        values : List[str]
            The search values.

        proteome_id : str
            TODO: Currently implementation would fail if proteome_id is optional and None, either we should make it not optional or implement checks. 
            I guess would be best to make it non optional. 
            Uniprot Reference Proteome ID. If provided only features of the proteome is provided.

        columns : List[str]
            The list of columns to be searched for. 

        Raises
        ------
        Exception 
            If provided search columns are not in the allowed list. 
            #TODO Should probably be a ValueError instead of an Exception? 
        """

        if columns is None:
            strs_columns = ["proteins", "genes"]
        else:
            strs_columns = [value for value in columns if value in ["entry", "proteins", "genes"]] 

            if not strs_columns:
                raise Exception("Columns provided are not allowed. Please use entry, proteins or genes only.")
        #check if proteome_id exists, None will throw an error here. 
        if proteome_id not in self._cached_features: raise ValueError(f"proteome_id {proteome_id} not found.")
        #results_or = [False] * self._cached_features.shape[0]
        features = self._cached_features[proteome_id]
        #create regex to search for all values at the same time 
        reg_exp = build_regex_for_search(search_strings=values)
        #bool data frame to store results, default false
        search_result = pd.DataFrame(data = np.zeros(shape=(features.shape[0],len(strs_columns))), 
                                     dtype=bool, 
                                     index = features.index,
                                     columns = strs_columns)
        for str_column in strs_columns:
            # added proteome_id here.
            search_result.loc[:,str_column] = features[str_column].str.contains(pat=reg_exp,case=False,regex=True)
        #check for any match
        results_or = search_result.any(axis=1)

        return self._cached_features[proteome_id].loc[results_or,:]

    def get(self, keys : List[str] = None, proteome_id: str = None, ignoreMissing = False) -> pd.DataFrame:
        """
        Returns a Pandas DataFrame of all features if no keys are defined, or items matching the keys. 
        May throws KeyError Exception if key is not in the annotation table. 
        Set ignoreMissing to true to return only matching rows. Returns multiple rows if key is not unique. 
        Will throw a KeyError exception for the wrong proteome_id.
        
        Parameters
        ----------
        keys : List[str]
            Feature keys (Uniprot ids)
        proteome_id : str, default None
            Uniprot Reference Proteome ID. If provided only features of the proteome is provided.
        ignoreMissing : bool, default False #TODO rename to match proteome_id style? 
            If true missing keys are simply ignore, otherwise an Exception is thrown. 
        Raises
        ------
        KeyError 
            if proteome_id is unknown. 
        """

        if proteome_id is None:
            collected_features = pd.DataFrame(index=[],
                                              columns=["entry", "proteins", "genes", "organism", "organism_id", #removing "key" since it is the index? otherwise nan everywhere
                                                       "aa_length", "mass", "proteome_id"])
            if keys is None:
                for proteome_id_loop, item in self._cached_features.items(): 
                    #item should be named features? In update item is dir and the values of the dict are called features.
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
            #TODO check if proteome_id exists otherwise throw error/warning. Should we only check in cached_features? At the moment they are all loaded. 
            if proteome_id not in self._cached_features: raise ValueError(f"proteome_id {proteome_id} not found.")
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
        """
        Imports the annotation tables defined in the configurations. 
        Keeps only first entry if duplicate rows are imported.
        Expects tab delimited files. 
        
        Raises
        ------
        FileNotFoundError 
            If the path does not exist.
            If feature database file is missing. 
            If mapping file is not found.
        Exception
            If an import error pd.read_csv(...) is thrown of the database file or the mapping file.
        """
        self._lock.acquire()
        self._featureFiles = []
        self._cached_features = {}

        dir_root = ANNOTATION_SETTINGS.path_features

        if not os.path.exists(dir_root): # instead of throwing an error, we can also warn and create the folder, of course there
            # no annotations then present.
            self._lock.release()
            raise FileNotFoundError(f"Invalid feature database path {dir_root}.")

        for item in os.scandir(dir_root):
            if item.is_dir():

                featureFile = os.path.join(dir_root,item.name,ANNOTATION_SETTINGS.file_features) #"%s/%s/%s" % (dir_root, item.name, ANNOTATION_SETTINGS.file_features) #os save
                mappingFile = os.path.join(dir_root,item.name,ANNOTATION_SETTINGS.file_features_column_mappings)  #"%s/%s/%s" % (dir_root, item.name, ANNOTATION_SETTINGS.file_features_column_mappings) #os save

                if not os.path.exists(featureFile):
                    self._lock.release()
                    raise FileNotFoundError(f"Missing feature database file {featureFile}.")  # ToDo: Change to a Warning? Would at least ensure that the backend still starts.

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

                #not sure if we want to keep source in the mappings file? As well as the download link. Probably not? One could then omit the 
                #first filtering step. 
                
                #find mappings "from" that exist and subset them
                from_found = mappings.loc[:,"from"].isin(features.columns) 
                mapping_subset = mappings.loc[from_found,:]
                #get the key column name in the original data (e.g. Entry)
                
                #create the dataset
                features = pd.DataFrame(
                    data = features.loc[:,mapping_subset.loc[:,"from"].values].values , 
                    columns = mapping_subset.index.values).set_index("key")
                features.fillna(value="", inplace=True)
                #remove na indices (if for example the file contained extra lines, then remove duplicates)
                features = features.loc[features.index.dropna().drop_duplicates(keep="first"),:] 
       
                # print(features)
                # print(mappings)
                # features = pd.concat([features.loc[:, mappings.loc["entry"][0]],
                #                       features.loc[:, mappings.loc["key"][0]],
                #                       features.loc[:, mappings.loc["proteins"][0]],
                #                       features.loc[:, mappings.loc["genes"][0]],
                #                       features.loc[:, mappings.loc["organism"][0]],
                #                       features.loc[:, mappings.loc["organism_id"][0]],
                #                       features.loc[:, mappings.loc["aa_length"][0]],
                #                       features.loc[:, mappings.loc["mass"][0]]],
                #                      axis=1)
                
               
                # features.rename(columns={mappings.loc["entry"][0]: "entry",
                #                          mappings.loc["key"][0]: "key",
                #                          mappings.loc["proteins"][0]: "proteins",
                #                          mappings.loc["genes"][0]: "genes",
                #                          mappings.loc["organism"][0]: "organism",
                #                          mappings.loc["organism_id"][0]: "organism_id",
                #                          mappings.loc["aa_length"][0]: "aa_length",
                #                          mappings.loc["mass"][0]: "mass"},
                #                 inplace=True)
                   

                # pd.DataFrame(index=[],# columns=["entry", "key", "proteins", "genes", "organism", "organism_id", "aa_length", "mass"])
                # self._cached_features = pd.concat([self._cached_features, features], axis=0)
                self._cached_features[item.name] = features
                #self._cached_features[item.name].fillna(value="", inplace=True)
                #FYI : this ignores indeces (https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.drop_duplicates.html) 
                #and we should remove doubled indices (e.g. keys) but not same entries, here you had key in the data before so it was likely fine.
                #self._cached_features[item.name].drop_duplicates(keep="first", inplace=True) 
                #self._cached_features[item.name].set_index("key", inplace=True)

                self._featureFiles.append(featureFile)

        self._lock.release()

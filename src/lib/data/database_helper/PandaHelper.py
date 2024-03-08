import pandas as pd 
import typing
from typing import List, Dict, Any, Tuple, Optional, Literal
from collections import OrderedDict
from pydantic import BaseModel, Field, field_serializer
from threading import Lock
from abc import abstractmethod
from lib.data.database_helper.ABCDatabaseHelper import MCDatabaseHelper
from config.models.submissions.submissions import DatasetSubmissionModel, SubmissionCountResponse
from services.json import read_json
import os 
import numpy as np 
import time 


from config.settings.db import get_db_settings
from config.enums.states import SubmissionStates


DB_SETTINGS = get_db_settings()

class PandaDatabaseHelper(MCDatabaseHelper):
    """
    Database Helper 
    """
    def __init__(self, instrument_attribute_tag : str = "att_ms_name", stale_time : int = 10) -> None:
        super().__init__()
        self._lock = Lock()  # Synchronization primitive to make it multi-threading safe
        self._updated_timestamp = None 
        self._stale_time_s = stale_time #10 second stale time (not updating even if there are new files.)
        self._last_update = {}
        self._labels_by_feature = None #key feature_key -> values (set of dataset labels)
        self._labels_by_attribute_tag = None #find datasets which have the attribute assigned 
        self._labels_by_attribute_value_tag = None
        self._labels_by_genotype = None
        self._labels_by_string_search = None
        self._labels_by_state = None
        self._labels_by_user = None
        self._labels_by_organism = None
        self._organism_by_label = None
        self._attribute_value_tags_by_label = None
        self._attribute_tags_by_label = None
        self._scaled_variance_by_feature = None
        self._mean_abundance_by_feature = None 
        self._labels = set() # all submission/dataset labels 
        self._instruments = set()
        self._labels_with_data_table = set() #all labels that have a datatable.
        self._number_samples_by_instrument = None
        self._turnover_time = None #the time a projects takes from submission 
        self._instrument_attribute_tag = instrument_attribute_tag
        self._instrument_first_use = None
        self._labels_by_instrument = None
        self._features_by_label = None
                
    def _add_value(self, d : Dict, k : str, label : str):
        """_summary_

        Parameters
        ----------
        d : Dict
            _description_
        v : str
            _description_
        """
        if k not in d:
            d[k] = set([label])
        else:
            if label not in d[k]:
                d[k].add(label)
                
    def _get_count(self, d : Dict[str,set], k_subset : Optional[set] = None, label_subset : Optional[set] = None) -> Dict[str,Dict[str,set|int]]:
        """Counts the number of submission labels in a dictionary. 

        Parameters
        ----------
        d : Dict
            A dictionary that that contains a certain value as as key such as attribute_tag, attribute_value_tag or feature and values
            present a set of submission/dataset labels that match that key (e.g. that contain the feature or that are annotated by the specific
            attribute tag.)
        k_subset : Optional[set], optional
            A set of keys that should be considered. If None all keys will be returned, by default None
        label_subset : Optional[set], optional
            Set of submission labels that should be included. This should be used if the count of submission that contain
            a specific set of keys should be counted, by default None

        Returns
        -------
        Dict[str,Dict[str,set|int]]
            Returns a dictionary that contains certain information for each key in dict d. 
            The list is the same length as the provided dict, unless a subset of keys ``k_subset`` is defined,
            then the length of the dict equals ``k_subset.length``. 
            ```
            [
            {"submission_labels" : labels, #the labels that match key 
            "submission_count" : intersection_length} #the count e.g. the length of the set of labels. 
            ]
            ```
        """
        k_subset_active = k_subset is not None
        if label_subset is None:
            return dict([(k,{"submission_labels" : labels, "submission_count" : len(labels)}) for k, labels in d.items() if not k_subset_active or k in k_subset])
        else:
            counts = {}
            for k, labels in d.items():
                if k_subset_active and k not in k_subset: continue
                label_subset_match = set.intersection(label_subset,labels)
                intersection_length = len(label_subset_match)
                if intersection_length > 0:
                    counts[k] = {"submission_labels" : label_subset_match, "submission_count" : intersection_length}
            return counts
        
    def _get_value(self, d : Dict, k : str, split_string : str = ";", join : Literal["inner","outer"] = "inner"):
        """_summary_

        Parameters
        ----------
        d : Dict
            _description_
        k : str
            _description_
        split_string : str, optional
            _description_, by default ";"
        join : Literal[&quot;inner&quot;,&quot;outer&quot;], optional
            _description_, by default "inner"

        Returns
        -------
        _type_
            _description_
        """
        if split_string in k:
            ks = k.split(";")
            sets = [self._get_value(d,k) for k in ks if k in d]
            return set.intersection(*sets) if join == "inner" else set.union(*sets)
        else:
            if k in d: return d[k]
            else: return set( )
    
    def _get_value_from_int_key(self, d : Dict, k : str|int, split_string : str = ";", join : Literal["inner","outer"] = "inner"):
        
        if isinstance(k,str) and split_string in k:
            ks = [int(float(k)) for k in k.split(";")]
            
            sets = [d[k] for k in ks if k in d]
            return set.intersection(*sets) if join == "inner" else set.union(*sets)
        else:
            if isinstance(k,str):
                k = int(float(k))
            if k in d: return d[k]
            else: return set()

    def _get_last_modified(self, path : str) -> Dict:
        """_summary_

        Parameters
        ----------
        path : str
            _description_

        Returns
        -------
        Dict
            _description_
        """
        file_stamps = {}
        self._metadata_count = 0
        self._datatable_count = 0
        if os.path.exists(path):
            folder = os.walk(path)
            for root, folder, files in folder:
                #no metadata - no loading 
                if "params.json" not in files: continue 
                for file in files:
                    if file in ["params.json","data.txt"]:
                        isMetaData = file == "params.json"
                        filePath = os.path.join(root,file)
                        file_stamps[filePath] = {
                            "st_mtime" : os.stat(filePath).st_mtime, 
                            "label" : os.path.basename(root), 
                            "param_file" : os.path.join(root,"params.json"),
                            "is_param" : isMetaData}
                    # print(os.stat(filePath))
                    # print("=====")
        return file_stamps
    
    def _get_files_to_update(self):
        """
        """          
        files_modified = dict([(filePath,fileProps) 
                          for filePath, fileProps in self._get_last_modified(DB_SETTINGS.db_datadir).items() 
                          if self._updated_timestamp is None or fileProps["st_mtime"] > self._updated_timestamp])
        if len(files_modified) == 0:
            return 
        
        self._load_data_tables(files_modified)
        self._load_metadata(files_modified)
        
    def _load_data_tables(self, files_modified : Dict) -> None:
        """Reads datatable from text file, but only the Key (index) column.

        Parameters
        ----------
        files_modified : Dict
            _description_
        """
        if self._mean_abundance_by_feature is None:
            self._mean_abundance_by_feature = {} 
        if self._scaled_variance_by_feature is None:
            self._scaled_variance_by_feature = {}
        if self._features_by_label is None:
            self._features_by_label = {}
            
        feature_keys = []
        for filePath, fileProps in files_modified.items():
            if not fileProps["is_param"]:
                try:
                    d = pd.read_csv(filePath, sep="\t", index_col="Key") #use_cols = "Key"
                except:
                    print("error loading file: ",filePath," Missing 'Key' column?")
                    continue
                d["label"] = fileProps["label"]
                feature_keys.append(d.loc[:,["label"]])
                self._labels_with_data_table.add(fileProps["label"])
                self._features_by_label[fileProps["label"]] = d.index
                #add mean 
                try:
                    metadata = DatasetSubmissionModel(**read_json(fileProps["param_file"]))
                except Exception as e:
                    print(e,filePath)
                sample_names = metadata.sample_names
                
                self._mean_abundance_by_feature[fileProps["label"]] = d.loc[:,sample_names].mean(axis=1).to_dict()
                # load meta to calculate variances 
                    
                total_variance = d.loc[:,sample_names].var(axis=1)
                sample_attributes = metadata.samples_attributes
                sample_genotypes = metadata.samples_genotypes
                samples_attrs_genotype = {**{"att_genotype" : sample_genotypes}, **sample_attributes}
                vars = dict([(attribute_tag,pd.DataFrame(index=d.index)) for attribute_tag in samples_attrs_genotype.keys()])
                for attribute_tag, sample_attrs in samples_attrs_genotype.items():
                    for sample_att_value_tag,sample_indices in sample_attrs.items():
                        sample_names_attrs = [sample_names[sample_idx] for sample_idx in sample_indices]
                        variance = d.loc[:,sample_names_attrs].var(axis=1)
                        vars[attribute_tag].loc[d.index,sample_att_value_tag] = total_variance / variance
                    vars[attribute_tag] = vars[attribute_tag].max(axis=1)
                
                #concat relative variances
                max_relative_vars = pd.concat(list(vars.values()),axis=1).max(axis=1).to_dict()
                self._scaled_variance_by_feature[fileProps["label"]] = max_relative_vars

                              
        if len(feature_keys) == 0: return
        merged_features = pd.concat(feature_keys)
        if self._labels_by_feature is None:
            self._labels_by_feature = dict([(feature_key,set(feature_data["label"].values)) for feature_key, feature_data in merged_features.groupby(level=0)])
        else:
            for feature_key, feature_data in merged_features.groupby(level=0):
            
                if feature_key in self._labels_by_feature:
                    ## very heavy from computation time, TODO : adapt this. 
                    labels = feature_data["label"].values
                    # The code `self._labels_by_feature` is likely creating or accessing a variable
                    # named `_labels_by_feature` within a Python class or object. This variable may be
                    # used to store labels associated with specific features or attributes.
                    self._labels_by_feature[feature_key].update(labels)
                    
    def _handle_instrument_attribute(self, attribute_value_tag : str, metadata : DatasetSubmissionModel):
        
        self._instruments.add(attribute_value_tag)
        if attribute_value_tag not in self._number_samples_by_instrument:
            self._number_samples_by_instrument[attribute_value_tag] = []
        self._number_samples_by_instrument[attribute_value_tag].append(len(metadata.sample_names)) 
        if attribute_value_tag not in self._instrument_first_use:
            self._instrument_first_use[attribute_value_tag] = metadata.created_on        
        elif self._instrument_first_use[attribute_value_tag] > metadata.created_on:
            self._instrument_first_use[attribute_value_tag] = metadata.created_on
            
        if attribute_value_tag not in self._labels_by_instrument:
            self._labels_by_instrument[attribute_value_tag] = []
        # TODO naming is conistent with labels_by_instrument since it does not return the labels but rather a small summary.. is this required??
        self._labels_by_instrument[attribute_value_tag].append({"label" : metadata.label, 
                                                                "create_on" : metadata.created_on, 
                                                                "title" : metadata.title, 
                                                                "user_label" : metadata.user_label,
                                                                "number_samples" : metadata.n_samples,
                                                                "number_features" : np.nan if metadata.label not in self._features_by_label else self._features_by_label[metadata.label].size})
            
    def _load_metadata(self, files_modified : Dict) -> None:
        """_summary_

        Parameters
        ----------
        files_modified : Dict
            _description_
        """
        if self._labels_by_attribute_tag is None:
            self._labels_by_attribute_tag = {}
        if self._labels_by_attribute_value_tag is None:
            self._labels_by_attribute_value_tag = {}
        if self._labels_by_genotype is None:
            self._labels_by_genotype = {}
        if self._labels_by_string_search is None:
            self._labels_by_string_search = {}
        if self._labels_by_state is None:
            self._labels_by_state = {}
        if self._labels_by_user is None:
            self._labels_by_user = {}
        if self._attribute_value_tags_by_label is None:
            self._attribute_value_tags_by_label = {}
        if self._attribute_tags_by_label is None:
            self._attribute_tags_by_label = {}
        if self._labels_by_organism is None:
            self._labels_by_organism = {}
        if self._organism_by_label is None:
            self._organism_by_label = {}
        if self._number_samples_by_instrument is None:
            self._number_samples_by_instrument = {}
        if self._instrument_first_use is None:
            self._instrument_first_use = {}
        if self._labels_by_instrument is None:
            self._labels_by_instrument = {}
        
        
        for filePath, fileProps in files_modified.items():
            if fileProps["is_param"]:
                try:
                    metadata = DatasetSubmissionModel(**read_json(filePath))
                except Exception as e:
                    print(e,filePath)
                if fileProps["label"] != metadata.label:
                    continue 
                
                ### save label
                self._labels.add(metadata.label)
                ### add dataset attributes
                dataset_attributes = metadata.dataset_attributes
                for attribute_tag in dataset_attributes.keys():
                    self._add_value(self._labels_by_attribute_tag,attribute_tag,metadata.label)
                    self._add_value(self._attribute_tags_by_label,metadata.label,attribute_tag)
                    
                    for attribute_value_tag in dataset_attributes[attribute_tag]:
                        self._add_value(self._labels_by_attribute_value_tag,attribute_value_tag,metadata.label)
                        self._add_value(self._attribute_value_tags_by_label,metadata.label,attribute_value_tag)
                        ### save instrument 
                        if attribute_tag == self._instrument_attribute_tag:
                            self._handle_instrument_attribute(attribute_value_tag,metadata)
                            # 
                            
                            # if attribute_value_tag not in self._number_samples_by_instrument:
                            #     self._number_samples_by_instrument[attribute_value_tag] = []
                            # self._number_samples_by_instrument[attribute_value_tag].append(len(metadata.sample_names))
                        ### save organism, TODO make organism tag definable in the constructor. 
                        if attribute_tag == "att_organism":
                            self._add_value(self._labels_by_organism,attribute_value_tag,metadata.label)
                            self._add_value(self._organism_by_label,metadata.label,attribute_value_tag)
                        
                        
                ### add sample attributes 
                for attribute_tag, sample_attribute in metadata.samples_attributes.items():
                    self._add_value(self._labels_by_attribute_tag,attribute_tag,metadata.label)
                    self._add_value(self._attribute_tags_by_label,metadata.label,attribute_tag)
                    for sample_attribute_value_tag in sample_attribute.keys():
                        if attribute_tag == self._instrument_attribute_tag:
                            self._handle_instrument_attribute(sample_attribute_value_tag,metadata)
                        # add organism here? 
                        self._add_value(self._labels_by_attribute_value_tag,sample_attribute_value_tag,metadata.label)
                        self._add_value(self._attribute_value_tags_by_label,metadata.label,sample_attribute_value_tag)
                        

                ### add genotypes 
                samples_genotypes = metadata.samples_genotypes
                for genotype_label in samples_genotypes.keys():
                    self._add_value(self._labels_by_genotype,genotype_label,metadata.label)
                
                ###add_search_string
                if metadata.label not in self._labels_by_string_search:
                    self._labels_by_string_search[metadata.label] = OrderedDict()
                    for n,text in enumerate([metadata.title, metadata.label] + list(metadata.metatext.values())):
                        self._labels_by_string_search[metadata.label][n] = text.lower() 
                     
                ##add states 
                self._add_value(self._labels_by_state,metadata.state,metadata.label)
                
                ###add users
                self._add_value(self._labels_by_user,metadata.user_label,metadata.label)
                if len(metadata.collaborators) > 0:
                    for user_label in metadata.collaborators:
                        self._add_value(self._labels_by_user,user_label,metadata.label)
        
    def get_all_labels(self):
        """_summary_
        """
        self.update()
        return self._labels
    
    def get_attribute_value_tags_by_labels(self, 
                                           labels : str, 
                                           split_string = ";", 
                                           join = Literal["inner","outer"], 
                                           count : bool = True, 
                                           attribute_value_subset : str = None, 
                                           attribute_subset : str = None) -> Tuple[set,Dict[str|int,SubmissionCountResponse]]:
        
        counts = {}
        self.update() 
        attribute_value_tags = self._get_value(self._attribute_value_tags_by_label,labels,split_string,join)
        if attribute_value_subset is not None:
            #subset the attribute value tags before counting.
            attribute_value_subset = attribute_value_subset.split(split_string)
            attribute_value_tags = [attribute_value_tag for attribute_value_tag in attribute_value_tags if attribute_value_tag in attribute_value_subset]

        if attribute_subset is not None:
            #subset the attributes before counting.
            attribute_subset = attribute_subset.split(split_string)
            attribute_value_tags = [attribute_value_tag for attribute_value_tag in attribute_value_tags if any(attribute_value_tag.startswith(attribute_tag) for attribute_tag in attribute_subset)]
       
        if count:
            label_subset = set(labels.split(split_string))
            counts = self._get_count(self._labels_by_attribute_value_tag,k_subset=attribute_value_tags, label_subset=label_subset)
            
        return attribute_value_tags, counts
        

    def get_attribute_tags_by_labels(self, labels : str, split_string = ";", join = Literal["inner","outer"], count : bool = True) -> Tuple[set,Dict[str|int,SubmissionCountResponse]]:
        """_summary_

        Parameters
        ----------
        labels : str
            _description_
        split_string : str, optional
            _description_, by default ";"
        """
        counts = {}
        self.update() 
        attribute_tags = self._get_value(self._attribute_tags_by_label,labels,split_string,join)
        if count:
            label_subset = set(labels.split(split_string))
            counts = self._get_count(self._labels_by_attribute_tag,k_subset=attribute_tags, label_subset=label_subset)
            
        return attribute_tags, counts
        
    def get_metadata_count(self):
        """Provides the number of metadata in the database.
        """
        self.update()
        return len(self._labels)

    def get_datatable_count(self):
        """Provides the number of datatables (e.g. published)
        """
        self.update()
        return len(self._labels_with_data_table)
    
    def get_instruments(self):
        self.update() 
        return self._instruments
    
    def get_instrument_first_use(self, instrument_tag : str = None) -> float|Dict[str,float]:
        self.update()
        if instrument_tag is not None:
            if instrument_tag not in self._instrument_first_use: raise ValueError("Instrument tag not found.")
            return self._instrument_first_use[instrument_tag]
        
        return self._instrument_first_use
        
    def get_number_features(self) -> int:
        """Returns the number of unique features in the database.

        Returns
        -------
        int
            The total number of features in the database.
        """
        self.update()
        return len(self._labels_by_feature)
    
    def get_number_genotypes(self) -> int:
        
        self.update()
        return len(self._labels_by_genotype)
    
    def get_sample_number_by_instrument(self) -> Dict[str,List[int]]:
        """Returns the number of samples per instrument. 

        Returns
        -------
        _type_
            _description_
        """
        self.update()
        return self._number_samples_by_instrument
        
    def get_labels(self, state : int|str = None, user_label : str = None, feature_key : str = None, attribute_tag : str = None, attribute_value_tag : str = None, genotype_label : str = None, join : Literal["inner","outer"] = "inner") -> set:
        
        feature_key_labels = None
        attribute_tag_labels = None
        attribute_value_tag_labels = None
        genotype_labels = None
        state_labels = None
        user_label_labels = None #dataset labels
        if state is not None:
            state_labels = self.get_labels_by_state(state)
        if feature_key is not None:
            feature_key_labels = self.get_labels_by_feature(feature_key)
        if user_label is not None:
            user_label_labels = self.get_labels_by_user_label(user_label)
        if attribute_tag is not None: 
            attribute_tag_labels = self.get_labels_by_attribute_tag(attribute_tag)
        if attribute_value_tag is not None: 
            attribute_value_tag_labels = self.get_labels_by_attribute_value_tag(attribute_value_tag)
        if genotype_label is not None: 
            genotype_labels = self.get_labels_by_genotype_label(genotype_label)
        
        #merge/intersect the sets by join
        label_sets = [s for s in [state_labels,feature_key_labels,attribute_tag_labels,attribute_value_tag_labels,genotype_labels, user_label_labels] if s is not None]
        if len(label_sets) == 0: return set()
        if join == "inner":
            #if any is empty, the intersection will also be empty 
            if any(len(s) == 0 for s in label_sets): return set()
            return set.intersection(*label_sets)
        elif join == "outer":
            return set.union(*label_sets)
        else:
            raise ValueError("Given join method is not known.")
    
    def get_organisms_by_label(self, labels : str, split_string = ";", join = Literal["inner","outer"], count : bool = True) -> Tuple[set,Dict[str|int,SubmissionCountResponse]]:
        counts = {}
        self.update() 
        organism_value_tags = self._get_value(self._organism_by_label,labels,split_string,join)
        if count:
            counts = self._get_count(self._labels_by_organism,k_subset=organism_value_tags)
            
        return organism_value_tags, counts
    
    def get_labels_by_instrument(self, instrument_tag : str) -> List[Dict]:
        
        self.update()
        if instrument_tag not in self._labels_by_instrument: return []
        return self._labels_by_instrument[instrument_tag]
        
                    
    def get_labels_by_organism(self, organism_tag : str):
        """"""
        self.update() 
        return self._get_value(self._labels_by_organism, organism_tag)
            
    def get_labels_by_search_string(self, query : str, subset : set = None) -> List[str]:
        """
        
        """
        lower_query = query.lower()
        subset_labels = subset is not None and len(subset) > 0
        self.update() 
        
        matched_labels =  []
        for label, texts in self._labels_by_string_search.items():
            if not subset_labels or label in subset:
                for id, text in texts.items():
                    if lower_query in text:
                        matched_labels.append((label,id))
                        break
        #if title matched put the submission to front (as it got the id 0, label is 1, any other metatexst is > 1)
        matched_labels.sort(key = lambda x: x[1])
        return [x[0] for x in matched_labels]
                    
    def get_labels_by_state(self, state : int|str) -> set:
        """_summary_

        Parameters
        ----------
        state : int
            _description_

        Returns
        -------
        set
            _description_
        """
        self.update()
        return self._get_value_from_int_key(self._labels_by_state,state,join="outer")
                    
    def get_labels_by_feature(self, feature_key : str) -> set:
        """"""
        self.update()
        return self._get_value(self._labels_by_feature,feature_key)
    
    def get_label_count_by_feature(self, k_subset : set = None, label_subset : set = None) -> Dict[str|int,SubmissionCountResponse]:
        self.update()
        return self._get_count(self._labels_by_feature,k_subset,label_subset)
    
    def get_labels_by_attribute_tag(self, attribute_tag : str) -> set:
        """_summary_

        Parameters
        ----------
        attribute_tag : str
            _description_

        Returns
        -------
        set
            _description_
        """
        self.update()
        return self._get_value(self._labels_by_attribute_tag,attribute_tag)
    
    def get_label_count_by_attribute_tag(self, k_subset : set = None, label_subset : set = None) -> Dict[str|int,SubmissionCountResponse]:
        """_summary_
        """
        self.update()
 
        return self._get_count(self._labels_by_attribute_tag,k_subset,label_subset)
    
    def get_labels_by_attribute_value_tag(self, attribute_value_tag : str ) -> set:
        """_summary_

        Parameters
        ----------
        attribute_value_tag : str
            _description_

        Returns
        -------
        set
            _description_
        """
        self.update()
        return self._get_value(self._labels_by_attribute_value_tag,attribute_value_tag)
    
    def get_label_count_by_attribute_value_tag(self, k_subset : set = None, label_subset : set = None) -> Dict[str|int,SubmissionCountResponse]:
        """_summary_
        """
        return self._get_count(self._labels_by_attribute_value_tag,k_subset,label_subset)
        
    def get_labels_by_genotype_label(self, genotype_label : str) -> set:
        """_summary_

        Parameters
        ----------
        genotype_label : str
            _description_

        Returns
        -------
        set
            _description_
        """
        self.update()
        return self._get_value(self._labels_by_genotype,genotype_label)
    
    def get_label_count_by_genotype(self, k_subset : set = None, label_subset : set = None) -> Dict[str|int,SubmissionCountResponse]:
        self.update()
        return self._get_count(self._labels_by_genotype, k_subset, label_subset)
    
    def get_label_count_by_user(self, k_subset : set = None, label_subset : set = None) -> Dict[str|int,SubmissionCountResponse]:
        """_summary_
        """
        self.update() 
        return self._get_count(self._labels_by_user,k_subset,label_subset)
            
    def get_label_count_by_state(self, k_subset : set = None, label_subset : set = None):
        """TODO reconsider naming, since there is also get_labels_by_state to get the labels by an exact state.

        Returns
        -------
        _type_
            _description_
        """
        self.update() 
        return self._get_count(self._labels_by_state, k_subset, label_subset)
    
    def get_labels_by_user_label(self, user_label : str) -> set:
        self.update()
        return self._get_value(self._labels_by_user,user_label)
           
           
    def get_label_count_by(self, by : Literal["feature","state","user","attribute_value_tag","attribute_tag","genotype"] = None, k_subset : set = None, label_subset : set = None) -> Dict[str|int,SubmissionCountResponse]:   
      
        if by is None:
            #return all submission counts 
            return {"submissions" : { 
                "submission_count" : self.get_metadata_count(), 
                "submission_labels" : self.get_all_labels()
                }}
        elif by == "feature": return self.get_label_count_by_feature(k_subset,label_subset)
        elif by == "state": return self.get_label_count_by_state(k_subset,label_subset)
        elif by == "user": return self.get_label_count_by_user(k_subset,label_subset)
        elif by == "attribute_value_tag": return self.get_label_count_by_attribute_value_tag(k_subset,label_subset)
        elif by == "attribute_tag": return self.get_label_count_by_attribute_tag(k_subset,label_subset)
        elif by == "genotype": return self.get_label_count_by_genotype(k_subset,label_subset) 
        

    def get_rel_variance_by_feature(self, feature_key : str, labels : str = None) -> pd.DataFrame:
        """_summary_

        Parameters
        ----------
        feature_key : str
            _description_
        labels : str, optional
            _description_, by default None
        """
        self.update()
        if labels is None:
            labels = self.get_all_labels()
        scaled_variance = []
        for label in labels:
            if label in self._scaled_variance_by_feature and feature_key in self._scaled_variance_by_feature[label]:
                scaled_feature_var = self._scaled_variance_by_feature[label][feature_key]
                scaled_variance.append((label,scaled_feature_var))
        df = pd.DataFrame(scaled_variance,columns=["label","scaled_variance"])
        return df
    
    def get_abundance_by_feature(self,feature_key : str, labels : str = None) -> pd.DataFrame:
        """_summary_

        Parameters
        ----------
        feature_key : str
            _description_
        labels : str, optional
            _description_, by default None

        Returns
        -------
        pd.DataFrame
            _description_
        """
        self.update()
        if labels is None:
            labels = self.get_all_labels()
        mean_abundances = []
        for label in labels:
            if label in self._mean_abundance_by_feature and feature_key in self._mean_abundance_by_feature[label]:
                abundance = self._mean_abundance_by_feature[label][feature_key]
                mean_abundances.append((label,abundance))
        df = pd.DataFrame(mean_abundances,columns=["label","abundance"])
        return df
        

    def update(self):
        """_summary_
        """
        if self._updated_timestamp is None or time.time()-self._updated_timestamp > self._stale_time_s:
            self._get_files_to_update()
            self._updated_timestamp = time.time()
        
        
import typing 
from typing import Optional
import pandas as pd 


from lib.data.dataset.ABCDataset import MCDataset 
import os 
import json 
from config.models.submissions.submissions import DatasetSubmissionModel
from config.settings.db import get_db_settings

DB_SETTINGS = get_db_settings()

class PandaFileDataset(MCDataset):
    """Replacement for the Data.Dataset"""
    # Todo: Write documentation
    def __init__(self,
                 dataset_id: int = -1,
                 label: str = None,
                 state: int = None,
                 title: str = None,
                 #experimentator: str = None,
                 user_label : str = None,
                 collaborators : typing.List[str] = [],
                 #name_group: str = None,
                 #contact_email: str = None,  # ToDo: Countercheck default values
                 created_on: float = None,  # ToDo: Check DataType Date
                 uploaded_on: str = None,
                 data_table: pd.DataFrame = None,
                 metatexts: typing.Dict = None,
                 urls: typing.List = [],
                 replicates: typing.List[int] = [],
                 attributes_dataset: typing.Dict = None,
                 attributes_samples: typing.Dict = None,
                 sample_names : typing.List[str] = [],
                 timeline : typing.Dict = None,
                # instrument: typing.Dict = None,
                 loadFromDatabase: bool = False, 
                 load_meta_only : bool = False):  # ToDo: Check DataType Date
        
        """Constructor"""
        # Todo: Write documentation
        super().__init__(
            created_on=created_on,
            uploaded_on=uploaded_on,
            title=title,
            dataset_id = dataset_id,
            state=state,
            user_label=user_label,
            data_table=data_table,
            label=label,
            urls=urls,
            collaborators=collaborators,
            attributes_dataset=attributes_dataset,
            attributes_samples=attributes_samples,
            sample_names = sample_names,
            metatexts=metatexts,
            replicates=replicates,
            timeline=timeline,
            loadFromDatabase=loadFromDatabase,
            load_meta_only=load_meta_only
        )

    def _readFromDatabase(self) -> None:
        """"""
        # Todo: Write documentation
        path_dataset = os.path.join(DB_SETTINGS.db_datadir,self._label)
        if not os.path.exists(path_dataset): raise Exception("Dataset not found.")
        path_data = os.path.join(path_dataset,"data.txt")

        if os.path.exists(path_data):
            data = pd.read_csv(path_data, sep="\t", index_col="Key")
            data = data.loc[data.index.dropna(), :]  # remove nan index  # ToDo: Should we really remove NAs?
            self._cached_data_table = data
            self._data_uploaded = True
       
        self._read_meta()
    #     self._state = meta["state"]
    #     self._user_label = meta["user_label"]
    #     self._title = meta["title"]
    #     self._collaborators = meta["collaborators"]
    #         #self._experimentator = meta["experimentator"]
    #    # self._name_group = meta["group_name"]
    #     #self._contact_email = meta["email"]
    #     self._created_on = meta["created_on"]
    #     self._modified_on = meta["modified_on"] if "modified_on" in meta else None #stupid check should be avoided
    #    # self._uploaded_on = meta["date_uploaded_on"]
    #    # self._instrument = meta["instrument"]
    #     self._metatexts = meta["metatexts"]
    #     self._urls = meta["links"]
    #     self._attributes_dataset = meta["dataset_attributes"]
    #     self._attributes_samples = meta["samples_attributes"]
    #     self._sample_names = meta["sample_names"]

    def _read_meta(self, meta : Optional[DatasetSubmissionModel] = None) -> None:
        """"""
        path_dataset = os.path.join(DB_SETTINGS.db_datadir,self._label) # TO DO: CHange this, 
        path_meta = os.path.join(path_dataset,"params.json")
        
        if os.path.exists(path_meta) and meta is None:
            with open(path_meta,"r+") as file: #ensure proper closing 
                meta_file = json.load(file)
                meta = DatasetSubmissionModel(**meta_file)
        if meta is None: raise Exception("Dataset seems to be missing params.", self._label)
        self._state = meta.state
        self._user_label = meta.user_label
        self._title = meta.title
        self._collaborators = meta.collaborators
        self._replicates = meta.replicates
            #self._experimentator = meta["experimentator"]
    # self._name_group = meta["group_name"]
        #self._contact_email = meta["email"]
        self._created_on = meta.created_on
        self._modified_on = meta.modified_on
    # self._uploaded_on = meta["date_uploaded_on"]
    # self._instrument = meta["instrument"]
        self._metatexts = meta.metatext
        self._urls = meta.links
        self._attributes_dataset = meta.dataset_attributes
        self._attributes_samples = meta.samples_attributes
        self._sample_names = meta.sample_names
        self._timeline = meta.timeline
        
    def get_meta_data(self, meta : Optional[DatasetSubmissionModel] = None) -> DatasetSubmissionModel:
        """
        """
        if meta is None:
            self._read_meta()
        return DatasetSubmissionModel(
            title=self._title,
            replicates=self._replicates,
            n_samples=len(self._sample_names),
            label=self._label, 
            state=self._state,
            user_label=self._user_label,
            created_on=self._created_on,
            samples_attributes=self._attributes_samples,
            dataset_attributes=self._attributes_dataset,
            metatext=self._metatexts,
            collaborators=self._collaborators,
            sample_names=self._sample_names,
            timeline=self._timeline)

    def write(self):
        """"""
        # Todo: Write documentation
        str_dir = os.path.join(DB_SETTINGS.db_datadir,self._label)
        if not os.path.exists(str_dir):
            os.mkdir(str_dir)
            params_path = os.path.join(str_dir,"params.json")
            self._cached_data_table.to_csv(path_or_buf=str_dir+"data.txt",
                                           sep="\t", index_col="Key")

            with open(params_path, "w") as file_out:
                json.dump(self.getMetaJson(), file_out)
        else:
            raise Exception(f"A dataset with id {self._id} already exists.")


    def write_json(self, meta : DatasetSubmissionModel, update : bool = True):
        ""
        str_dir = os.path.join(DB_SETTINGS.db_datadir,self._label)
        if not os.path.exists(str_dir):
            os.mkdir(str_dir)
        params_path = os.path.join(str_dir,"params.json")

        with open(params_path, "w") as file_out:
            json.dump(meta.model_dump(exclude_none=True), file_out, indent=4)
        if update:
            ##update dataset object
            self._read_meta(meta)

    def hasData(self):
        """"""
        path_dataset_data = os.path.join(DB_SETTINGS.db_datadir,self._label,"data.txt")
        return os.path.exists(path_dataset_data)
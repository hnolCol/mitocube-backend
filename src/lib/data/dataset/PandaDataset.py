import typing 
import pandas as pd 


from lib.data.dataset.ABCDataset import MCDataset 
import os 
import json 

from config.settings.db import get_db_settings

DB_SETTINGS = get_db_settings()

class PandaFileDataset(MCDataset):
    """Replacement for the Data.Dataset"""
    # Todo: Write documentation
    def __init__(self,
                 dataset_id: int = -1,
                 label: str = None,
                 state: str = None,
                 title: str = None,
                 #experimentator: str = None,
                 user_id : int = None,
                 #name_group: str = None,
                 contact_email: str = None,  # ToDo: Countercheck default values
                 created_on: float = None,  # ToDo: Check DataType Date
                 uploaded_on: str = None,
                 data_table: pd.DataFrame = None,
                 metatexts: typing.Dict = None,
                 urls: typing.List = None,
                 replicates: typing.Dict = None,
                 attributes_dataset: typing.Dict = None,
                 attributes_samples: typing.Dict = None,
                # instrument: typing.Dict = None,
                 loadFromDatabase: bool = False, 
                 load_meta_only : bool = False):  # ToDo: Check DataType Date
        
        """Constructor"""
        # Todo: Write documentation
        super().__init__(dataset_id, label, state,
                         title, user_id, contact_email,
                         created_on, uploaded_on,
                         data_table, metatexts, urls, replicates, attributes_dataset, attributes_samples,
                         loadFromDatabase, load_meta_only)

    def _readFromDatabase(self) -> None:
        """"""
        
        # Todo: Write documentation
        path_dataset = os.path.join(DB_SETTINGS.db_datadir,self._label)
        if not os.path.exists(path_dataset): raise Exception("Dataset not found.")
        path_data = os.path.join(path_dataset,"data.txt")

        data = pd.read_csv(path_data, sep="\t", index_col="Key")
        data = data.loc[data.index.dropna(), :]  # remove nan index  # ToDo: Should we really remove NAs?

        self._cached_data_table = data
        meta = self._read_meta()
        self._state = meta["state"]
        self._user_label = meta["user_label"]
        self._title = meta["title"]
            #self._experimentator = meta["experimentator"]
       # self._name_group = meta["group_name"]
        self._contact_email = meta["email"]
        self._created_on = meta["created_on"]
       # self._uploaded_on = meta["date_uploaded_on"]
       # self._instrument = meta["instrument"]
        self._metatexts = meta["metatexts"]
       # self._urls = meta["urls"]
        self._attributes_dataset = meta["attributes_dataset"]
        self._attributes_samples = meta["attributes_samples"]

    def _read_meta(self) -> None:
        """"""
        path_dataset = os.path.join(DB_SETTINGS.db_datadir,self._label) # TO DO: CHange this, 
        path_meta = os.path.join(path_dataset,"params.json")
        
        if os.path.exists(path_meta):
            with open(path_meta,"r+") as file: #ensure proper closing 
                meta = json.load(file)
            return meta 
        

    def write(self):
        """"""
        # Todo: Write documentation
        str_dir = os.path.join(DB_SETTINGS.db_datadir,self._id)
        if not os.path.exists(str_dir):
            os.mkdir(str_dir)

            self._cached_data_table.to_csv(path_or_buf=str_dir+"data.txt",
                                           sep="\t", index_col="Key")

            with open(str_dir+"params.json", "w") as file_out:
                json.dump(self.getMetaJson(), file_out)
        else:
            raise Exception(f"A dataset with id {self._id} already exists.")

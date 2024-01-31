import typing 
from typing import Optional
import pandas as pd 
import os 

from deprecated import deprecated

from lib.data.dataset.ABCDataset import MCDataset 

from services.json import save_json, read_json

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
                 user_label : str = None,
                 collaborators : typing.List[str] = [],
                 created_on: float = None,  # ToDo: Check DataType Date
                 uploaded_on: str = None,
                 data_table: pd.DataFrame = None,
                 metatexts: typing.Dict = None,
                 urls: typing.List = [],
                 replicates: typing.List[int] = [],
                 attributes_dataset: typing.Dict = None,
                 attributes_samples: typing.Dict = None,
                 samples_genotypes : typing.Dict = None,
                 sample_names : typing.List[str] = [],
                 timeline : typing.Dict = None,
                 loadFromDatabase: bool = False, 
                 load_meta_only : bool = False):  
        
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
            samples_genotypes = samples_genotypes,
            sample_names = sample_names,
            metatexts=metatexts,
            replicates=replicates,
            timeline=timeline,
            loadFromDatabase=loadFromDatabase,
            load_meta_only=load_meta_only
        )

    def _readFromDatabase(self) -> None:
        """
        Raises
        ------
        Exception 
            If the path to the dataset does not exist. 
        """
        # Todo: Write documentation
        path_dataset = os.path.join(DB_SETTINGS.db_datadir,self._label)
        if not os.path.exists(path_dataset): raise Exception("Dataset not found.")
        path_data = os.path.join(path_dataset,"data.txt")

        if os.path.exists(path_data):
            data = pd.read_csv(path_data, sep="\t", index_col="Key")
            data = data.loc[data.index.dropna(), :]  # remove nan index  # ToDo: Should we really remove NAs?
            #yes only if the key is nan, not when any kind of value is nan 
            self._cached_data_table = data
            self._data_uploaded = True
       
        self._read_meta()

    def _read_meta(self, meta : Optional[DatasetSubmissionModel] = None) -> None:
        """
        Reads the meta data of a dataset and sets the dataset class params. 

        Parameters
        ----------
        meta : DatasetSubmissionModel, optional
            The meta data of the dataset. If provided, the params.json file for the
            specific dataset will not be loaded. 

        Raises
        ------
        Exception
            If the params.json file is missing.
        """
        path_dataset = os.path.join(DB_SETTINGS.db_datadir,self._label) # TO DO: CHange this, 
        path_meta = os.path.join(path_dataset,"params.json")
        
        if os.path.exists(path_meta) and meta is None:
            meta_file = read_json(path_meta)
            meta = DatasetSubmissionModel(**meta_file)
        if meta is None: raise Exception("Dataset seems to be missing params.", self._label)
        self._state = meta.state
        self._user_label = meta.user_label
        self._title = meta.title
        self._collaborators = meta.collaborators
        self._replicates = meta.replicates
        self._created_on = meta.created_on
        self._modified_on = meta.modified_on
        self._metatexts = meta.metatext
        self._urls = meta.links
        self._attributes_dataset = meta.dataset_attributes
        self._attributes_samples = meta.samples_attributes
        self._samples_genotypes = meta.samples_genotypes
        self._sample_names = meta.sample_names
        self._timeline = meta.timeline
        self._runlist = meta.runlist
        
    @deprecated("Please use getMetaJson from the MCDataset abstract class.")
    def get_meta_data(self) -> DatasetSubmissionModel:
        """
        Returns the meta data of a dataset.
        
        Returns
        -------
        DatasetSubmissionModel
            The meta information of the dataset.

        """
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
            timeline=self._timeline,
            runlist=self._runlist,
            links=self._urls)

    def write(self):
        """"""
        # Todo: Write documentation
        str_dir = os.path.join(DB_SETTINGS.db_datadir,self._label)
        if not os.path.exists(str_dir):
            os.mkdir(str_dir)
            meta_path = os.path.join(str_dir,"params.json")
            self._cached_data_table.to_csv(path_or_buf=str_dir+"data.txt",
                                           sep="\t", index_col="Key")
            save_json(self.getMetaJson().model_dump(exclude_none=True),meta_path)
        else:
            raise Exception(f"A dataset with id {self._id} already exists.")


    def write_json(self, meta : DatasetSubmissionModel, update : bool = True):
        """
        Writes the submission details to a json file.
        If the directory does not exists, it will be created in a folder 
        at ../<db_datadir>/<label>
        
        Parameters
        ----------

        meta : DatasetSubmissionModel
            The pydantic model that holds the meta information/details for a submission

        update : bool, default True
            If True the meta data are updated for the dataset by calling _read_meta
        
        Raises
        ------
            TypeError 
                If meta is not of type pydantic DatasetSubmissionModel 
        """

        if not isinstance(meta, DatasetSubmissionModel): raise TypeError('Meta must be of type DatasetSubmssionModel')
        str_dir = os.path.join(DB_SETTINGS.db_datadir,self._label)
        if not os.path.exists(str_dir):
            os.mkdir(str_dir) 
        meta_path = os.path.join(str_dir,"params.json")
        save_json(meta.model_dump(exclude_none=True),meta_path)
        if update:
            ##update dataset object
            self._read_meta(meta)

    def hasData(self):
        """Returns true of a data.txt file is found for the dataset label."""
        path_dataset_data = os.path.join(DB_SETTINGS.db_datadir,self._label,"data.txt")
        return os.path.exists(path_dataset_data)
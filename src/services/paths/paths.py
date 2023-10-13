import os
from typing import List
from pathlib import Path
from services.paths.utils import check_dir_exists
from config.settings.db import DB


PATHS = [
    "dynamic",
    "static",
    "static/datasets",
    "dynamic/submissions",
    "dynamic/tokens",
    "dynamic/performance"
]


class Paths:
    """Class to check and provide resource for paths"""
    def __init__(self, app_root : str, db_settings : DB) -> None:
        self.root = app_root
        self.db_settings = db_settings 
        self.resource_path = self.__build_path_resources()
        self.__check_dirs()

    def __build_path_resources(self):
        """"""
        data_dir = self.db_settings.db_datadir
        return os.path.join(self.root,data_dir)

    def __check_dirs(self):
        """Checks dirs and creates them if not existance"""
        for p in PATHS:
            check_dir_exists(os.path.join(self.resource_path,p),makeParents=True)

    @property
    def datesets(self) -> Path:
        """Returns path to dir which stores datasets"""
        return Path(os.path.join(self.resource_path,"static","datasets"))
    
    @property
    def performance(self) -> Path:
        """Returns path to dir which stores performance files"""
        return Path(os.path.join(self.resource_path,"dynamic","performance"))

    @property
    def submissions(self) -> Path:
        """Returns path to dir which stores datasets"""
        return Path(os.path.join(self.resource_path,"dynamic","submissions"))
    
    @property
    def tokens(self) -> Path:
        """Returns path to a file which stores tokens."""
        return Path(os.path.join(self.resource_path,"dynamic","tokens.json"))
        


    

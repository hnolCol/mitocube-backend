
from functools import lru_cache

from pydantic_settings import BaseSettings
from pydantic import IPvAnyAddress
from pydantic import SecretStr
from pydantic import FilePath
from pydantic import DirectoryPath
from typing import Literal, Optional

class DB(BaseSettings):
    """Base Settings"""

    data_id_length : int = 8 #length of the dataID (randomly generated string)

    attribute_file : FilePath = "/Users/hnolte/Documents/GitHub/mitocube-backend/resources/attributes/attributes.json"

    db_handler :Literal["pandafiles","postgresql"] = "pandafiles"  # ToDo: use class names instead?
    
    db_datadir : DirectoryPath = "/Users/hnolte/Documents/GitHub/mitocube-backend/resources/data"
    db_userdir : DirectoryPath = "/Users/hnolte/Documents/GitHub/mitocube-backend/resources/users"
    # db_features : DirectoryPath = "/Users/hnolte/Documents/GitHub/mitocube-backend/resources/annotations"  # ToDo: Question, should annotation (as DB) also be here?

    db_ip : Optional[IPvAnyAddress] = "127.0.0.1"  # ToDo: create validation conditions if db_handler is postgresql?
    db_user : Optional[str] = None
    db_name : Optional[str] = None
    db_pw : Optional[SecretStr] = None
    db_max_dataset_cached : int = 100

    
    
    class Config:
        env_file = ".env"
        extra = "ignore"

@lru_cache()
def get_db_settings():
    return DB()

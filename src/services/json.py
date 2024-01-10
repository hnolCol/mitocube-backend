import json 
from typing import Any

def save_json(data : dict | str, file_path : str, encoding : str = "utf-8", indent : int = 4):
    """
    Saves data into a json file.
    Note that the file_path is  not altered, hence the extension .json
    should be included. 
    It is not checked if the file exists already. Existing files will silently
    overwritten. 
    

    Parameters
    ----------
    data : dict | str 
        The data that should be saved into a json file 
    file_path : str
        The file path to the json file. 
    encoding : str, default utf-8
        The encoding used to save the json file. 
    indent : int, default 4 
        The indent to be used in json.dump()
    """
    with open(file_path,"w+", encoding=encoding) as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)


def read_json(file_path : str) -> Any:
    """
    Reads a json file. 

    Parameters
    ----------
    file_path : str
        The file path to the json file. 
    Returns
    -------
    Any 
        The json file content.
    """
    with open(file_path,"r+") as f:
        json_data = json.load(f)
    return json_data
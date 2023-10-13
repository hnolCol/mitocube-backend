

## Dont move this file to another location as it based on the parents to find 
## the root path.
import os 
from pathlib import Path
from typing import Tuple

rootFilePath = Path(os.path.abspath(__file__))

def check_dir_exists(path : str, makeParents : bool = True) -> Tuple[bool,str]:
    """Checks if path to dir exists."""
    if not makeParents:
        return os.path.exists(path), path
    else:
        p : Path = Path(path)
        p.mkdir(parents=True,exist_ok=True)
        return os.path.exists(p), path
    
def join_path(*args) -> str:
    """Return joined path"""
    return os.path.join(*args)

def get_absolute_path(path) -> Path:
    """Returns the absolute path in a pathlib Path object"""
    return Path(os.path.abspath(path))

def get_absolute_path_to_dir(path) -> Path:
    return Path(os.path.abspath(path)).parent


def getRootPath():
    """Returns the root path of the backend"""
    return rootFilePath.parents[2]

def getPathToResources():
    """Returns path to resources root/resources"""
    rootPath : Path = rootFilePath.parents[2]
    pathToResource = os.path.join(rootPath,"resources")
    if not os.path.exists(pathToResource): raise FileNotFoundError("Could not find resource folder.") #DirNotFoundError? 
    return pathToResource




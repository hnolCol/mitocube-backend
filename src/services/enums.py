
from enum import Enum 

from typing import List, Dict

def get_enum_values_as_list_of_strings(enum : Enum) -> List[str]:
    """Returns a list of all values in an Enum"""
    return [str(e.value) for e in enum]

def get_inversed_enum_as_dict(enum : Enum) -> Dict:
    """Returns an enum as a dict"""
    
    return {e.value  : e.name for e in enum}

def get_enum_as_dict(enum : Enum, keyFrom : Enum = None) -> Dict:
    """Returns an enum as a dict"""
    if keyFrom is None:
        return {e.name: e.value for e in enum}
    else:
        return {e_key.value: enum[e_key.name].value for e_key in keyFrom}


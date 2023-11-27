
from collections import OrderedDict
from typing import List
import numpy as np 

def value_mapper_from_dict(d : dict, value_is_index : bool = False, values : List = [str]) -> OrderedDict:
    """
    Takes a dictionary and creates a mapper for the values
    to map the defined keys
    """
    m = OrderedDict()
    for k, v in d.items():
        if isinstance(v,str):
            m[v] = k 
        elif isinstance(v,int):
            if value_is_index and len(values) >= v+1:
                m[v] = values[v]
        elif isinstance(v,list) or isinstance(v,np.ndarray):
            for vv in v:
                if vv in m:
                    m[vv] += " "+k
                else:
                    m[vv] = k
    return m 
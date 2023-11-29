## generate attributes from excel

# Script to generate the required attributes.json file from an Excel file.
# The attributes and attributes_values sheet in the Excel file are used to manage them. 
# Please note that at some point admins will be able to create and edit attributes from the 
# user interface. 
# The excel file can contain extra columnns they will simply be ignore when loading the files
# using the attribute pydantic base model. 

# Please adjust the absolute file paths. 

import pandas as pd 

import numpy as np 
from json import JSONEncoder, dump
import math 

__last_modified__ = "20231120"
__author__ = "Hendrik Nolte"

    
FILE = "/Users/hnolte/Documents/GitHub/mitocube-backend/resources/attributes/attributes.xlsx"
FILE_OUT = "/Users/hnolte/Documents/GitHub/mitocube-backend/resources/attributes/attributes.json"

ATTRIBUTE_SHEET = "attributes"
ATTRIBUTE_VALUES_SHEET = "attribute_values"




def nan2None(obj):
    if isinstance(obj, dict):
        return {k:nan2None(v) for k,v in obj.items()}
    elif isinstance(obj, list):
        return [nan2None(v) for v in obj]
    elif isinstance(obj, float) and math.isnan(obj):
        return None
    return obj

class NanConverter(JSONEncoder):
    def default(self, obj):
        # possible other customizations here 
        pass
    def encode(self, obj, *args, **kwargs):
        obj = nan2None(obj)
        return super().encode(obj, *args, **kwargs)
    def iterencode(self, obj, *args, **kwargs):
        obj = nan2None(obj)
        return super().iterencode(obj, *args, **kwargs)

attr = pd.read_excel(FILE,sheet_name=ATTRIBUTE_SHEET)
attr_values = pd.read_excel(FILE,sheet_name=ATTRIBUTE_VALUES_SHEET)

attrs = attr.dropna(how="all")
attrs["id"] = np.arange(attrs.index.size)
tag_mapper = dict([(tag,id) for tag,id in attrs[["tag","id"]].values])
parent_ids = attrs["parent_tag"].map(tag_mapper)

attrs.loc[:,"parent_id"] = parent_ids 
attr_values.loc[:,"attribute_id"] = attr_values["attribute_tag"].map(tag_mapper)
attr_values = attr_values.dropna(how="all")
attr_values.dropna(subset=["attribute_id"], inplace=True)
attr_values["id"] = np.arange(attr_values.index.size)


JSON = {"attributes" : attrs.to_dict(orient="records"), "attribute_values" : attr_values.to_dict(orient="records")}

with open(FILE_OUT,"w+") as f:
    dump(JSON,f,indent=4, cls=NanConverter)

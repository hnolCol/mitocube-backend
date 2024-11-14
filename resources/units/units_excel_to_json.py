import pandas as pd 
import json 
import math 
X = pd.read_excel("Units.xlsx").fillna("")


print(X)

json_data = [] 



def nan2None(obj):
    if isinstance(obj, dict):
        return {k:nan2None(v) for k,v in obj.items()}
    elif isinstance(obj, list):
        return [nan2None(v) for v in obj]
    elif isinstance(obj, float) and math.isnan(obj):
        return None
    return obj

class NanConverter(json.JSONEncoder):
    def default(self, obj):
        # possible other customizations here 
        pass
    def encode(self, obj, *args, **kwargs):
        obj = nan2None(obj)
        return super().encode(obj, *args, **kwargs)
    def iterencode(self, obj, *args, **kwargs):
        obj = nan2None(obj)
        return super().iterencode(obj, *args, **kwargs)


for UnitType, data in X.groupby("UnitType"):
    print(UnitType, data, data["type_priority"].values[0])
    json_data.append({
        "text" : UnitType,
        "tag" : data["UnitType tag"].values[0],
        "priority": int(data["type_priority"].values[0]),	
        "units" : data[["tag","text","priority"]].to_dict(orient="records")
    })
with open("units.json","w") as f:
    
    json.dump(json_data,f,indent = 4, cls=NanConverter)



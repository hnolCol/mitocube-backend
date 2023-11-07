import json 


def save_json(data : dict, file_path : str):
    """Saves a json file"""
    with open(file_path,"w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def read_json(file_path : str):
    """"""
    with open(file_path,"r+") as f:
        json_data = json.load(f)
    return json_data
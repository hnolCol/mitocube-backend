import json 


def save_json(data : dict, file_path : str):
    """Saves a json file"""
    with open(file_path,"w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

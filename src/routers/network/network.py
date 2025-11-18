from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from typing import List, Literal



from services.users import is_user_admin, get_user_from_token


from lib.data.statistic.Ttest import Ttest

from config.settings.db import get_db_settings
from config.settings.network import get_network_settings
from config.models.user import UserModel
from config.models.attributes import AttributeValueModel
from config.enums.states import SubmissionStatesEnums



import json 
import os 
import numpy as np 
import pandas as pd 
router = APIRouter(
    prefix="/api/networks",
    tags=["Networks"]
    )

NETWORK_SETTINGS = get_network_settings()
SOURCE_loc_human = os.path.join(NETWORK_SETTINGS.network_dir,"mitocarta_human","localization.json")
SOURCE_P_human = os.path.join(NETWORK_SETTINGS.network_dir,"mitocarta_human","pathway.json")
SOURCE_loc_mouse = os.path.join(NETWORK_SETTINGS.network_dir,"mitocarta_mouse","localization.json")
SOURCE_P_mouse = os.path.join(NETWORK_SETTINGS.network_dir,"mitocarta_mouse","pathway.json")
#TODO create network database, just for testing!! 
try:
    with open(SOURCE_loc_human,"r") as f:
        loc_pos_human = json.load(f)
    with open(SOURCE_P_human,"r") as f:
        loc_path_human = json.load(f)
except:
    loc_path_human = {}
    loc_pos_human = {}
    
try:
    with open(SOURCE_loc_mouse,"r") as f:
        loc_pos_mouse = json.load(f)
    with open(SOURCE_P_mouse,"r") as f:
        loc_path_mouse = json.load(f)
except:
    loc_path_mouse = {}
    loc_pos_mouse = {}
    
NETWORKS = {"UP000000589" : {"localization" : loc_pos_mouse, "pathway" : loc_path_mouse}, "UP000005640" : {"localization" : loc_pos_human, "pathway" : loc_path_human}}
    
def map_nodes(node,stats,stat_name):
    if "key" not in node: return None 
    key = node["key"]
    if key in stats.index:
        return stats.loc[key,stat_name]
    
    return None 

@router.get("/mitocarta/{dataset_label}")
def get_network(dataset_label : str, 
                network_type : Literal["pathway","localization"],
                sample_attribute_tag : str, 
                attribute_value_tag_left : str, 
                attribute_value_tag_right : str, 
                within_attribute_tag : str = None, 
                within_attribute_value_tag : str = None, 
                impute : bool = False,
                split_string : str = ";"
                ):
    pass

    # db = MCDatabase.getDatabase()
    # attributes_db = MCAttributes.getAttributeDatabase()
    # feature_db = PandaFeatureDatabase()
    # genotype_db = MCGenotypes.getGenotypeDatabase()
    # stats = pd.DataFrame() 
    # metadata = dataset.getMetaJson()
    # within_attribute_tag = within_attribute_tag.split(split_string) if within_attribute_tag is not None else []
    # within_attribute_value_tag = within_attribute_value_tag.split(split_string) if within_attribute_value_tag is not None else []
    # proteome_ids =  [organism.split(":")[1] for organism in metadata.dataset_attributes["att_organism"]]
    
    # if all(attr is not None for attr in [sample_attribute_tag,attribute_value_tag_left,attribute_value_tag_right]):
        
        
    #     #attribute_values = db_attributes.getAttributeValues(tags=[attribute_value_tag_left,attribute_value_tag_right,within_sample_attribute_value_tag]).set_index("tag", drop=False)
    #     #attribute = db_attributes.getAttributes(tags=[sample_attribute_tag,within_sample_attribute_tag]).set_index("tag")
        

        
    #     stats = Ttest(dataset).get_stats(sample_attribute_tag=sample_attribute_tag, 
    #                                  attribute_value_left=attribute_value_tag_left, 
    #                                  attribute_value_right=attribute_value_tag_right, suffix = comparison_suffix, 
    #                                  impute = impute,
    #                                  within_attribute_tag=within_attribute_tag,
    #                                  within_attribute_value_tag=within_attribute_value_tag)     
    # proteome_id = [proteome_id for proteome_id in proteome_ids if proteome_id in NETWORKS]
    # if len(proteome_id) == 0: raise HTTPException(status_code=404, detail = "No network found for this organism.")
    
    # network_props = NETWORKS[proteome_ids[0]][network_type]
    # if not stats.empty:
       
    #     stat_name = f"log2 FC {comparison_suffix}"
    #     nodes = [{**node, stat_name : map_nodes(node,stats,stat_name)}for node in network_props["nodes"]]
    #     network_props["nodes"] = nodes
    #     network_props["value_keyName"] = stat_name
    # return network_props
        
    # if network_type == "localization":
    #     ll = {**loc_pos}
    #     if not stats.empty:
            
    #         stat_name = f"log2 FC {comparison_suffix}"
    #         nodes = [{**node, stat_name : map_nodes(node,stats,stat_name)}for node in ll["nodes"]]
    #         ll["nodes"] = nodes
    #         ll["value_keyName"] = stat_name
    #     return ll
    # elif network_type == "pathway": 
    #     ll = {**loc_path}
    #     if not stats.empty:
            
    #         stat_name = f"log2 FC {comparison_suffix}"
    #         nodes = [{**node, stat_name : map_nodes(node,stats,stat_name)}for node in ll["nodes"]]
    #         ll["nodes"] = nodes
    #         ll["value_keyName"] = stat_name
    #     return ll
    

#[{"x" : v[0], "y" : v[1], "node_type" : "Pathway" if " " in k else "Feature", "label" : k, "value" : np.random.normal(loc=2,scale=0.2)} for k,v in pos.items()]
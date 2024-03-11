from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from typing import List, Literal
from lib.data.database.ABCDatabase import MCDatabase, MCAttributes
from lib.data.genotype.ABCGenotypeDatabase import MCGenotypes
from lib.data.annotations.ABCAnnotations import PandaFeatureDatabase
from services.users import is_user_admin, get_user_from_token

from lib.data.database_helper.ABCDatabaseHelper import MCDatabaseHelper
from lib.data.statistic.Ttest import Ttest

from config.settings.db import get_db_settings
from config.settings.network import get_network_settings
from config.models.user import UserModel
from config.models.attributes import AttributeValueModel
from config.enums.states import SubmissionStates
from lib.user.UserHandling import UserDB


from services.submission import get_dataset_from_database
from services.attributes import get_suffix_from_attributes_and_attribute_tags
import json 
import os 
import numpy as np 
import pandas as pd 
router = APIRouter(
    prefix="/api/networks",
    tags=["Networks"]
    )

NETWORK_SETTINGS = get_network_settings()
SOURCE_loc = os.path.join(NETWORK_SETTINGS.network_dir,"mitocarta_human","localization.json")
SOURCE_P = os.path.join(NETWORK_SETTINGS.network_dir,"mitocarta_human","pathway.json")
#TODO create network database, just for testing!! 
try:
    with open(SOURCE_loc,"r") as f:
        loc_pos = json.load(f)
    with open(SOURCE_P,"r") as f:
        loc_path = json.load(f)
except:
    loc_path = {}
    loc_pos = {}
    
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
    

    db = MCDatabase.getDatabase()
    attributes_db = MCAttributes.getAttributeDatabase()
    feature_db = PandaFeatureDatabase()
    genotype_db = MCGenotypes.getGenotypeDatabase()
    stats = pd.DataFrame() 
    
    within_attribute_tag = within_attribute_tag.split(split_string) if within_attribute_tag is not None else []
    within_attribute_value_tag = within_attribute_value_tag.split(split_string) if within_attribute_value_tag is not None else []
    
    if all(attr is not None for attr in [sample_attribute_tag,attribute_value_tag_left,attribute_value_tag_right]):
        dataset = get_dataset_from_database(db,label=dataset_label)
        metadata = dataset.getMetaJson()
        proteome_ids =  [organism.split(":")[1] for organism in metadata.dataset_attributes["att_organism"]]
        #attribute_values = db_attributes.getAttributeValues(tags=[attribute_value_tag_left,attribute_value_tag_right,within_sample_attribute_value_tag]).set_index("tag", drop=False)
        #attribute = db_attributes.getAttributes(tags=[sample_attribute_tag,within_sample_attribute_tag]).set_index("tag")
        
        comparison_suffix = get_suffix_from_attributes_and_attribute_tags(sample_attribute_tag,attribute_value_tag_left,attribute_value_tag_right,attributes_db,genotype_db,feature_db,within_attribute_tag=within_attribute_tag,within_attribute_value_tag=within_attribute_value_tag)

        
        stats = Ttest(dataset).get_stats(sample_attribute_tag=sample_attribute_tag, 
                                     attribute_value_left=attribute_value_tag_left, 
                                     attribute_value_right=attribute_value_tag_right, suffix = comparison_suffix, 
                                     impute = impute,
                                     within_attribute_tag=within_attribute_tag,
                                     within_attribute_value_tag=within_attribute_value_tag)     
        
    if network_type == "localization":
        ll = {**loc_pos}
        if not stats.empty:
            
            stat_name = f"log2 FC {comparison_suffix}"
            nodes = [{**node, stat_name : map_nodes(node,stats,stat_name)}for node in ll["nodes"]]
            ll["nodes"] = nodes
            ll["value_keyName"] = stat_name
        return ll
    elif network_type == "pathway": 
        ll = {**loc_path}
        if not stats.empty:
            
            stat_name = f"log2 FC {comparison_suffix}"
            nodes = [{**node, stat_name : map_nodes(node,stats,stat_name)}for node in ll["nodes"]]
            ll["nodes"] = nodes
            ll["value_keyName"] = stat_name
        return ll
    

#[{"x" : v[0], "y" : v[1], "node_type" : "Pathway" if " " in k else "Feature", "label" : k, "value" : np.random.normal(loc=2,scale=0.2)} for k,v in pos.items()]
    
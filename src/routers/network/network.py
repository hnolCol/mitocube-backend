from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from typing import List, Literal
from lib.data.database.ABCDatabase import MCAttributes
from services.users import is_user_admin, get_user_from_token

from lib.data.database_helper.ABCDatabaseHelper import MCDatabaseHelper

from config.settings.db import get_db_settings
from config.settings.network import get_network_settings
from config.models.user import UserModel
from config.models.attributes import AttributeValueModel
from config.enums.states import SubmissionStates
from lib.user.UserHandling import UserDB
import json 
import os 
import numpy as np 
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
    
@router.get("/mitocarta")
def get_network(type : Literal["pathway","localization"]):
    if type == "localization": return loc_pos
    elif type== "pathway": return loc_path
#[{"x" : v[0], "y" : v[1], "node_type" : "Pathway" if " " in k else "Feature", "label" : k, "value" : np.random.normal(loc=2,scale=0.2)} for k,v in pos.items()]
    

from fastapi import APIRouter, Depends, HTTPException
from collections import OrderedDict
from typing import List 

from lib.data.database.Database import Database
from lib.data.database.ABCDatabase import MCDatabase
from lib.data.annotations.ABCAnnotations import PandaFeatureDatabase

from lib.data.statistic.ANOVA import OneWayANOVA
from lib.data.clustering.HierarchicalClustering import HierarchicalClustering

from config.exceptions.HTTPExceptions import no_data_found
from config.models.user import UserModel
from config.models.parameter import APIParamString
from config.models.filter import Filter, FilterProps
from services.users import get_user_from_token, is_user_admin
from services.submission import map_tags_to_attribute_in_metadata

DB = Database.DB()


router = APIRouter(
    prefix="/api",
    tags=["Heatmap"]
)
#heatmap endpoints 
@router.get("/filters",
            tags=["Filter"])
def get_available_filters(proteome_id : str = None, user : UserModel = Depends(get_user_from_token)) -> List[Filter]:
    """Returns the filter set that are available in the database.

    Parameters
    ----------
    proteome_id : str, optional
        The Uniprot proteome id, by default None
    user : UserModel, optional
        User inferred from the token, by default Depends(get_user_from_token)

    Returns
    -------
    List[Filter]
        Filters available in the database.
    """
    
    filters = DB.filters.get(proteome_id=APIParamString(param=proteome_id).param)
    return filters


@router.get("filters/{filter_tag}")
def get_filter(filter_tag : str, user : UserModel = Depends(get_user_from_token)):
    "" 
    features = DB.filters.get (tag = filter_tag)
    

@router.post("/filters")
def add_filter(filterProps : FilterProps,
               user : UserModel = Depends(is_user_admin)):
    """Adds a filter from a list of protein tags. Tags are not created if not existance, therefore you may 
    have to add a proteome prior to setting up the filter. 
    This function can only be executed by an admin. 

    Parameters
    ----------
    tag : str
        The tag that the filter should have. 
    proteome_id : str
        The uniprot reference proteome. 
    description : str
        Description of the filter. 
    user : UserModel, optional
        The user model inferred from the token, by default Depends(is_user_admin)
    """
    if DB.filters.exists(tag = filterProps.tag):
        raise HTTPException(status_code=409, detail = "The tag exists already. Please delete the filter first if you want to replace it.")

    DB.filters.add(protein_tags=filterProps.protein_tags,
                          proteome_id=filterProps.proteome_id, 
                          filter_tag = filterProps.tag, 
                          description=filterProps.description,
                          publication = filterProps.publication)
    
    


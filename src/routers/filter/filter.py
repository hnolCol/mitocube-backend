
from fastapi import APIRouter, Depends, HTTPException
from collections import OrderedDict
from typing import List 

from lib.database.Database import Database

from lib.data.clustering.HierarchicalClustering import HierarchicalClustering

from config.exceptions.HTTPExceptions import no_data_found_http_exception
from config.models.user import UserModel
from config.models.parameter import APIParamString
from config.models.filter import FilterModel, FilterProps
from services.users import get_user_from_token, is_user_admin


DB = Database.DB()


router = APIRouter(
    prefix="/api",
    tags=["Heatmap"]
)
#heatmap endpoints 
@router.get("/filters/q", response_model=List[str],
            tags=["Filter"])
def get_available_filters(proteome_tags : str = None, 
                          protein_tag : str = None, 
                          submission_tag : str = None,
                          user : UserModel = Depends(get_user_from_token),
                          
                          ) -> List[str]:
    """Returns the filter set that are available in the database.

    Parameters
    ----------
    proteome_tags : str, optional
        The Uniprot proteome tag. For multiple proteoms - separate by ';', by default None
    submission_tag : str, optional
        The submission tag for which an available filter is returned. 
    feature_tag : str, optional, 
        If a feature_tag is given, the filters for the specific featurer are returned. 
        Cannot handle multiple feature_tags (e.g. divided b ";" as in the proteome)
    user : UserModel, optional
        User inferred from the token, by default Depends(get_user_from_token)

    Returns
    -------
    List[Filter]
        Filters available in the database.
    """
    
    filter_tags = DB.filters.find(proteome_tags = APIParamString(param=proteome_tags).param,
                             submission_tags = APIParamString(param=submission_tag).param,
                            protein_tag = protein_tag)
    return filter_tags


@router.get("filters/{filter_tag}")
def get_filter(filter_tag : str, user : UserModel = Depends(get_user_from_token)) -> List[FilterModel]:
    ""
    filter = DB.filters.get (tag = filter_tag)
    return filter 

@router.post("/filters") 
def add_filter(filterProps : FilterProps,
               user : UserModel = Depends(is_user_admin)) -> bool :
    """Adds a filter from a list of protein tags. Tags are not created if not existance, therefore you may 
    have to add a proteome prior to setting up the filter. 
    This function can only be executed by an admin. 

    Parameters
    ----------
    tag : str
        The tag that the filter should have. 
    proteome_tag : str
        The uniprot reference proteome. 
    description : str
        Description of the filter. 
    user : UserModel, optional
        The user model inferred from the token, by default Depends(is_user_admin)
    """
    if DB.filters.exists(tag = filterProps.tag):
        raise HTTPException(status_code=409, detail = "The tag exists already. Please delete the filter first if you want to replace it.")


    ok, msg = DB.filters.add(protein_tags = filterProps.protein_tags,
                          proteome_tag = filterProps.proteome_tag, 
                          filter_text = filterProps.text,
                          filter_tag = filterProps.tag, 
                          description=filterProps.description,
                          publication = filterProps.publication)
    return ok 
    
    


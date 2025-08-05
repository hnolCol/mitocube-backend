from neo4j import Driver, Result 
from typing import List, Literal
import pandas as pd 

from lib.database.abstract.SpareParts import SparePartsABC

from config.models.spareparts import SparepartModel, SparepartResponseModel

class Neo4jSpareParts(SparePartsABC):
    
    def __init__(self, driver : Driver):
        
        self._driver = driver 
    
    def _utils_insert_from_file(self, file_path : str = "", *args, **kwargs):
        ""

        spare_parts = pd.read_csv(file_path, *args, **kwargs)
        #creating the models here checks if all the types are correct. 
        spare_part_models = [SparepartModel(**s, s = [s["text"],s["description"]]).model_dump(exclude_none=True) for s in spare_parts.to_dict(orient="records")] 
        query = (
            "UNWIND $parts as sp_props "
            "MERGE (s:SparePart {tag : sp_props.tag}) "
            "ON CREATE "
            "SET s.created_at = timestamp(), s.description = sp_props.description, s.priority = sp_props.priority, s.s = sp_props.s, s.text = sp_props.text, s.company = sp_props.company, "
            "s.price = sp_props.price, s.product_id = sp_props.product_id, s.link = sp_props.link "
            "ON MATCH "
            "SET s.modified_at = timestamp(), s.description = sp_props.description, s.priority = sp_props.priority, s.s = sp_props.s, s.text = sp_props.text, s.company = sp_props.company, "
            "s.price = sp_props.price, s.product_id = sp_props.product_id, s.link = sp_props.link "
            "RETURN count(s) as count"
        )
    
        r = self._driver.execute_query(query, parts = spare_part_models, routing_="w", result_transformer_=Result.value)
        print(f"The database contains {r} spare parts")
        
    def exists(self, tag : str) -> bool:
        "Checks if a spare part exists"
        
        query = "WITH EXISTS {(s:SparePart {tag : $tag})} as sp_exists RETURN sp_exists "
        exists = self._driver.execute_query(query, tag = tag, routing_ = "r")    
        return exists[0]
        
    def find(self, search_string : str = None, limit : int = None) -> List[str]:
        """Find spare part by a search string and returns the tags that match. 

        Parameters
        ----------
        search_string : str, optional
            The query string, by default ""
        limit : int, optional
            The maximum number of spare parts to be returned., by default 20

        Returns
        -------
        List[str]
            The spare part tags. 
        """
        query = "MATCH (s:SparePart) "
        if search_string is not None and len(search_string) > 0:
            query += "WHERE s.s CONTAINS $search_string "
        query += "RETURN s.tag ORDER BY s.priority "
        
        if limit is not None:
            query += "LIMIT $limit"
               
        sp_tags = self._driver.execute_query(query, 
                                              search_string = search_string.lower(), 
                                              limit = limit, 
                                              routing_="r", 
                                              result_transformer_=Result.value)
        
        return sp_tags
    
    def get(self, tag : str) -> SparepartResponseModel:
        "" 
        
        if not self.exists(tag):
            raise ValueError("Tag not associated with a spare part.")
        
        query = (
            "MATCH (s:SparePart {tag : $tag}) "
            "return properties(s) "
        )
        
        
        spareparts = self._driver.execute_query(query, tag = tag, routing_= "r", result_transformer_= Result.value)
        if len(spareparts) == 0: raise ValueError("Even though the tag exists, the database returned none.")
        return SparepartResponseModel(**spareparts[0])
    
    
    
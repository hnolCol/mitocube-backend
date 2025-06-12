from typing import Optional,List

from neo4j import Driver, Result

from lib.database.abstract.UnitTypes import UnitTypesABC
from config.models.unit import UnitTypeResponseModel

import pandas as pd 

class Neo4JUnitTypes( UnitTypesABC):
    
    def __init__(self, driver : Driver) -> None:
        self._driver = driver
        
        
    def has_attribute_unit_types(self, attribute_tag : str) -> bool:
        """Checks if an attribute has a unit type (should this be rather in the 
        attribute DB?)"""
        ""
        query = (
            "WITH EXISTS {(a:Attribute {tag : $tag})-[:HAS_UNIT_TYPE]->(unittype:UnitType)} as exists "
            "RETURN exists "
        )    
        r = self._driver.execute_query(query, tag = attribute_tag, result_transformer_=Result.value)
        return r[0]
        
        
    def get_unit_types(self) -> List:
        return super().get_unit_types()
    
    # def get_unit_type(self,tags : List[str]):
        
    #     query = (
    #         "MATCH (unittype:UnitType) "
    #         "WHERE unittype.tag in $tags "
    #         "RETURN propiertes(unittype) "
    #     )
        
    #     r = self._driver.execute_query(query, tags = tags, result_transformer_= Result.value)
    #     print(r)
    #     return 
    
    def get_units(self, tags: List[str]) -> List[UnitTypeResponseModel]:
        
        query = (
            "MATCH (unittype:UnitType)-[:HAS_UNIT]-(u:Unit) "
            "WHERE unittype.tag IN $tags "
            "WITH unittype, u "
            "ORDER BY unittype.priority, u.priority DESC "
            "RETURN unittype.tag AS unit_type_tag, "
            "       unittype.text AS unit_type_text, "
            "       unittype.priority AS unit_type_priority, "
            "       unittype.has_feature_value as has_feature_value, "
            "       unittype.is_feature_position as is_feature_position, "
            "       COLLECT({tag: u.tag, text: u.text, priority : u.priority, description : u.description}) AS units "
        )
        
        
        r = self._driver.execute_query(query, routing_="r", tags = tags, result_transformer_=Result.data)
        
        return [UnitTypeResponseModel(tag = x["unit_type_tag"],
                               text=x["unit_type_text"],
                               priority = x["unit_type_priority"],
                               has_feature_value = x["has_feature_value"],
                               is_feature_position = x["is_feature_position"],
                               units=sorted(x["units"], key= lambda x: -x["priority"])) for x in r]
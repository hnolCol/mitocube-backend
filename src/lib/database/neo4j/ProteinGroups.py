from typing import Optional,List

from neo4j import Driver, Result

from lib.database.abstract.ProteinGroups import ProteinGroupsABC

from config.models.filter import FilterModel
from config.models.annotations.feature import FeatureModel

import pandas as pd 

class Neo4JProteinGroups(ProteinGroupsABC):
    
    def __init__(self, driver : Driver) -> None:
        ""
        self._driver = driver 
    
    
    def count(self, submission_tag : str) -> int:
        ""
        query = (
            "MATCH (s:Submission {tag : $submission_tag})-[:HAS_SAMPLE]->(s:Sample)-[r:QUANTIFIED]->(pg:ProteinGroup) "
            "RETURN count(pg) "
        )
        
        r = self._driver.execute_query(query, routing_="r", submission_tag = submission_tag, result_transformer_=Result.value)
        return r[0] if len(r) > 0 else 0
    
    def exists(self, tag : str) -> bool:
        ""
        ""
        query = (
            "WITH EXISTS {(f:ProteinGroup {tag : $tag})} as group_exists "
            "RETURN group_exists "
        )    
        r = self._driver.execute_query(query, tag = tag, result_transformer_=Result.value)
        return r[0]
    
   
   
    def find(self, search_string : str, limit : int = 20) -> List[str]:
        ""
        query = (
            "MATCH (f:ProteinGroup)-[:HAS_PROTEINS]->(p:Protein) "
            "WHERE toLower(f.text) CONTAINS $search_string OR toLower(f.tag) CONTAINS $search_string OR toLower(p.text) CONTAINS $search_string OR toLower(p.tag) CONTAINS $search_string "
            "RETURN f.tag "
            
        )
        if limit is not None:
            query += "LIMIT $limit"
            
        r = self._driver.execute_query(query, routing_="r", result_transformer_=Result.value, search_string=search_string.lower(), limit=limit)
        return r
    
    def get(self, tag : str):
        "" 
        
        query = (
            "MATCH (f:ProteinGroup {tag : $tag})-[:HAS_PROTEINS]->(p:Protein) "
            "RETURN f.tag as tag, f.text as text, collect(p.tag) as protein_tags "
        )
        
        
        r = self._driver.execute_query(query, routing_="r", tag = tag, result_transformer_=Result.to_dict)
        return FilterModel(**r[0]) if len(r) > 0 else None
    
    
    def get_proteins(self, tag : str) -> List[str]:
        "Returns the proteins in a specific protein group."
        
        query = (
            "MATCH (f:ProteinGroup {tag : $tag})-[:HAS_PROTEINS]->(p:Protein) "
            "RETURN p.tag as protein_tag "
        )
        
        r = self._driver.execute_query(query, routing_="r", tag = tag, result_transformer_=Result.value)
        return r
    
    def insert(self, protein_tags : List[str], tag : str, text : str) -> bool:
        ""
        if self.exists(tag): raise ValueError(f"Protein group with tag {tag} already exists. Use the update function." )
        
        query = (
            "MERGE (pg:ProteinGroup {tag  : $tag }) "
            "ON CREATE SET pg.created_at = timestamp() "
            "ON MATCH SET pg.modified_at = timestamp() "
            "OPTIONAL MATCH (pg)-[r:HAS_PROTEINS]->(p:Protein) "
            "DELETE r "
            "WITH pg "
            "UNWIND $protein_tags as protein_tag "
            "MATCH (p:Protein {tag : protein_tag}) "
            "MERGE (pg)-[:HAS_PROTEINS]->(p) "
        )
        
        self._driver.execute_query(query, routing_="w", tag = tag, text = text, protein_tags = protein_tags)
        return True
    
    
    def delete(self, tag: str) -> bool:
        ""
        if not self.exists(tag): raise ValueError(f"Protein group with tag {tag} does not exist.")
        
        query = (
            "MATCH (pg:ProteinGroup {tag : $tag}) "
            "DETACH DELETE pg "
        )
        
        self._driver.execute_query(query, routing_="w", tag = tag)
        return True
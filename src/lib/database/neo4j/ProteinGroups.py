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
        """Counts the number of protein groups. If a submission tag is given, only counts protein groups associated with that submission (e.g. that were quantified).
        """
        query = (
            "MATCH (submission:Submission {tag : $submission_tag})-[:HAS_SAMPLE]->(s:Sample)-[r:QUANTIFIED]->(pg:ProteinGroup) "
            "RETURN count(DISTINCT pg.tag)"
        )
        
        r = self._driver.execute_query(query, routing_="r", submission_tag = submission_tag, result_transformer_=Result.value)
        return r[0] if len(r) > 0 else 0
    
    
    def insert_bulk(self, protein_groups : List[str], protein_group_separator : str = ";") -> int:
        ""
        not_existing = [pg for pg in protein_groups if not self.exists(pg)]
        if len(not_existing) == 0: return 0
        query = (
            "UNWIND $protein_groups as group_tag "
            "WITH group_tag, split(group_tag, $protein_group_separator) as protein_tags "
            "MERGE (pg:ProteinGroup {tag: group_tag}) "
            "ON CREATE SET pg.created_at = timestamp() "
            "ON MATCH SET pg.modified_at = timestamp() "
            "WITH pg, protein_tags "
            "UNWIND protein_tags as protein_tag "
            "MATCH (p:Protein {tag: protein_tag}) "
            "MERGE (pg)-[:HAS_PROTEINS]->(p) "
        )
        r = self._driver.execute_query(query, routing_="w", protein_groups = not_existing, protein_group_separator = protein_group_separator)
        return len(not_existing)
    
    def exists(self, tag : str) -> bool:
        ""
        ""
        query = (
            "WITH EXISTS {(f:ProteinGroup {tag : $tag})} as group_exists "
            "RETURN group_exists "
        )    
        r = self._driver.execute_query(query, tag = tag, result_transformer_=Result.value)
        return r[0]
    
   
   
    def find(self, search_string : str, submission_tag : str = None, limit : int = 20) -> List[str]:
        ""
        query = ("MATCH (f:ProteinGroup)-[:HAS_PROTEINS]->(p:Protein) ")
        if submission_tag is not None:
            query += "WHERE EXISTS {(f)<-[:QUANTIFIED]-(:Sample)<-[:HAS_SAMPLE]-(submission:Submission {tag : $submission_tag})} AND "       
        else:
            query += "WHERE "
        
        query += (
            "(toLower(f.tag) CONTAINS $search_string OR p.s CONTAINS $search_string) "
            "RETURN DISTINCT f.tag ")
        if limit is not None:
            query += "LIMIT $limit"
            
        r = self._driver.execute_query(query, routing_="r", result_transformer_=Result.value, search_string=search_string.lower(), limit=limit, submission_tag=submission_tag)
        return r
    
    def get(self, tag : str):
        "" 
        
        query = (
            "MATCH (f:ProteinGroup {tag : $tag})-[:HAS_PROTEINS]->(p:Protein) "
            "RETURN f.tag as tag, f.text as text, collect(p.tag) as protein_tags "
        )
        
        
        r = self._driver.execute_query(query, routing_="r", tag = tag, result_transformer_=Result.data)
        return r[0] if len(r) > 0 else None
    
    
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
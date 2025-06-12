from typing import List, Tuple, Literal
from neo4j import Driver, Result


from lib.database.abstract.ResearchGroup import ResearchGroupABC
from config.models.researchgroup import ResearchGroupInput, ResearchGroupModel


class Neo4JResearchGroup(ResearchGroupABC):
    
    def __init__(self, driver : Driver) -> None:
        self._driver = driver 
    
    def add_users(self, tag : str, user_tags : List[str]):
        ""
        if not self.exists(tag): raise ValueError("Research group with tag {tag} does not exist.")
        
        query = (
            "MATCH (rg:ResearchGroup {tag : $tag}) "
            "UNWIND $user_tags as user_tag "
            "MATCH (u:User {tag : user_tag}) "
            "MERGE (rg)<-[r:IS_PART_OF]-(u) "
            "ON CREATE "
            "SET r.created_at = timestamp() "
        )
        
        self._driver.execute_query(query, routing_="w", tag = tag, user_tags = user_tags)
        
        
         
    def delete(self, tag: str) -> bool:
        return super().delete(tag)
       
    def exists(self, tag: str) -> bool:
        ""
        query = (
            "WITH EXISTS {(rg:ResearchGroup {tag : $tag})} as rg_exists "
            "RETURN rg_exists "
            )    
        r = self._driver.execute_query(query, tag = tag, result_transformer_=Result.value)
        return r[0]
    
    def get(self, tags : List[str] = None, limit : int = None) -> List[ResearchGroupModel]:
        
        query = (
            "MATCH (rg:ResearchGroup) "
            
        )
        if tags is not None and isinstance(tags,list) and len(tags) > 0:
            query += "WHERE rg.tag in $tags "
            
        query += "RETURN properties(rg) "
        
        if limit is not None:
            query += "LIMIT $limit"

        r = self._driver.execute_query(query, routing_="r",result_transformer_=Result.value, tags = tags, limit = limit)
        print(r)
        
        return [ResearchGroupModel(**ri) for ri in r]
        
        
    def get_tags(self, limit : int = 40) -> List[str]:
        ""
        
        query = (
            "MATCH (rg:ResearchGroup) "
            "RETURN rg.tag ORDER BY rg.created_at DESC LIMIT $limit"
        )
        
        r = self._driver.execute_query(query, routing_="r", result_transformer_=Result.value, limit=limit)
        return r 
    
    def get_users(self, tag : str) -> List[str]:
        "Returns the user tags that are part of the research group"
        query = (
            "MATCH (rg:ResearchGroup {tag : $tag})<-[r:IS_PART_OF]-(u:User) "
            "RETURN collect(u.tag) "
        )
        
        r = self._driver.execute_query(query, tag = tag, routing_= "r", result_transformer_=Result.value)
        if len(r) == 0:  return []
        return r[0]
        
    def insert(self, research_group : ResearchGroupInput):
        "" 
        if self.exists(research_group.tag): raise ValueError("Tag exists already. Delete first or use the update function.")
        
        query = (
            "MERGE (rg:ResearchGroup {tag : $research_group.tag}) "
            "ON CREATE "
            "SET rg.created_at = timestamp(), rg.name =  $research_group.name, rg.abbreviation =  $research_group.abbreviation, "
            "rg.address =  $research_group.address, rg.email =  $research_group.email "   
            "ON MATCH "
            "SET rg.modified_at = timestamp(), rg.name =  $research_group.name, rg.abbreviation =  $research_group.abbreviation, "
            "rg.address =  $research_group.address, rg.email =  $research_group.email "   
        )
        
        r = self._driver.execute_query(query, routing_="w", research_group = research_group.model_dump(exclude_none=True))
        
        
        
    def remove_users(self, tag : str, user_tags): 

        if not self.exists(tag): raise ValueError("Research group with tag {tag} does not exist.")
        
        query = (
            "MATCH (rg:ResearchGroup {tag : $tag}) "
            "UNWIND $user_tags as user_tag "
            "MATCH (u:User {tag : user_tag}) "
            "MATCH (rg)<-[r:IS_PART_OF]-(u) "
            "DELETE r"
        )
        
        self._driver.execute_query(query, routing_="w", tag = tag, user_tags = user_tags)
        
        
        
    def update(self, research_group : ResearchGroupInput):
        "" 
        self.insert(research_group)
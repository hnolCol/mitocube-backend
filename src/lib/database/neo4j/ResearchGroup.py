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
    
    # def find(self, search_string : str, limit : int = 20) -> List[str]:
    #     ""
    #     query = (
    #         "MATCH (rg:ResearchGroup) "
    #         "WHERE toLower(rg.text) CONTAINS $search_string OR toLower(rg.abbreviation) CONTAINS $search_string OR toLower(rg.tag) CONTAINS $search_string "
    #         "RETURN rg.tag "
            
    #     )
    #     if limit is not None:
    #         query += "LIMIT $limit"
            
    #     r = self._driver.execute_query(query, routing_="r", result_transformer_=Result.value, search_string=search_string.lower(), limit=limit)
    #     return r

    def find(self, search_string: str = None, user_tags: List[str] = None, submission_tags: List[str] = None, limit: int = 40) -> List[str]:
        """Finds research group tags that match the search string, user tags, or submission tags."""
        
        if user_tags is not None:
            query = (
                "MATCH (rg:ResearchGroup)<-[:IS_PART_OF]-(u:User) "
                "WHERE u.tag IN $user_tags "
            )
            if submission_tags is not None:
                query += "AND EXISTS {(rg)<-[:IS_PART_OF]-(su:User)-[:CREATED|COLLABORATES]->(s:Submission) WHERE s.tag IN $submission_tags} "
        elif submission_tags is not None:
            query = (
                "MATCH (rg:ResearchGroup)<-[:IS_PART_OF]-(u:User)-[:CREATED|COLLABORATES]->(s:Submission) "
                "WHERE s.tag IN $submission_tags "
            )
        else:
            query = (
                "MATCH (rg:ResearchGroup) "
                "WHERE true "
            )
        
        if search_string is not None and search_string != "":
            query += "AND (toLower(rg.text) CONTAINS $search_string OR toLower(rg.abbreviation) CONTAINS $search_string OR toLower(rg.tag) CONTAINS $search_string) "
        
        query += "RETURN DISTINCT rg.tag as tag "
        
        if limit is not None:
            query += "LIMIT $limit"
        
        r = self._driver.execute_query(
            query,
            routing_="r",
            result_transformer_=Result.value,
            search_string=search_string.lower() if search_string is not None else None,
            user_tags=user_tags,
            submission_tags=submission_tags,
            limit=limit
        )
        return r
        
    
    def get(self, tag : str) -> ResearchGroupModel:
        
        query = (
            "MATCH (rg:ResearchGroup) "
            "WHERE rg.tag = $tag "
            "RETURN properties(rg) "
        )

        r = self._driver.execute_query(query, routing_="r",result_transformer_=Result.value, tag = tag)

        return ResearchGroupModel(**r[0]) if len(r) > 0 else None


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
        
        
    def get_users_count(self, tag : str) -> int:
        "Returns the number of users that are part of the research group"
        query = (
            "MATCH (rg:ResearchGroup {tag : $tag})<-[r:IS_PART_OF]-(u:User) "
            "RETURN count(u) "
        )
        
        r = self._driver.execute_query(query, tag = tag, routing_= "r", result_transformer_=Result.value)
        if len(r) == 0:  return 0
        return r[0]
    
    def insert(self, research_group : ResearchGroupInput):
        "" 
        if self.exists(research_group.tag): raise ValueError("Tag exists already. Delete first or use the update function.")
        
        query = (
            "MERGE (rg:ResearchGroup {tag : $research_group.tag}) "
            "ON CREATE "
            "SET rg.created_at = timestamp(), rg.text =  $research_group.text, rg.abbreviation =  $research_group.abbreviation, "
            "rg.address =  $research_group.address, rg.email =  $research_group.email "   
            "ON MATCH "
            "SET rg.modified_at = timestamp(), rg.text =  $research_group.text, rg.abbreviation =  $research_group.abbreviation, "
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


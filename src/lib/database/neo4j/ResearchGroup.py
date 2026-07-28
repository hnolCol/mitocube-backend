from typing import List, Tuple, Literal
from neo4j import Driver, Result
import pandas as pd 
from services.encryption import create_hierarchical_hash
from lib.database.abstract.ResearchGroup import ResearchGroupABC
from config.models.researchgroup import ResearchGroupInput, ResearchGroupModel


class Neo4JResearchGroup(ResearchGroupABC):
    
    def __init__(self, driver : Driver) -> None:
        self._driver = driver 
    
    def _utils_insert_from_file(self, file_path : str, *args, **kwargs) -> pd.DataFrame:
        """Inserts research groups from a txt file and returns a DataFrame with the generated tags."""
        tags = []
        df = pd.read_csv(file_path, *args, **kwargs)
        research_groups = [ResearchGroupInput(**row) for row in df.to_dict(orient="records")]
        for rg in research_groups:
            tag = create_hierarchical_hash(rg.model_dump())
            tags.append(tag)
            if self.exists(tag):
                print("Research group already exists: ", tag, rg.text)
                continue
            self.insert(tag, rg)
            print("Research group inserted: ", tag, rg.text)
        df.loc[:,"tag"] = tags 
        return df 
    
    def insert_users(self, tag : str, user_tags : List[str]):
        ""
        if not self.exists(tag): raise ValueError("Research group with tag {tag} does not exist.")
        
        query = (
            "MATCH (rg:ResearchGroup {tag : $tag}) "
            "UNWIND $user_tags as user_tag "
            "MATCH (u:User {tag : user_tag}) "
            "MERGE (rg)<-[r:MEMBER_OF]-(u) "
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

    def find(self, search_string: str = None, user_tags: List[str] = None, submission_tags: List[str] = None, limit: int = 40) -> List[str]:
        """Finds research group tags that match the search string, user tags, or submission tags."""
        
        if user_tags is not None:
            query = (
                "MATCH (rg:ResearchGroup)<-[:MEMBER_OF]-(u:User) "
                "WHERE u.tag IN $user_tags "
            )
            if submission_tags is not None:
                query += "AND EXISTS {(rg)<-[:MEMBER_OF]-(su:User)-[:CREATED|COLLABORATES]->(s:Submission) WHERE s.tag IN $submission_tags} "
        elif submission_tags is not None:
            query = (
                "MATCH (rg:ResearchGroup)<-[:MEMBER_OF]-(u:User)-[:CREATED|COLLABORATES]->(s:Submission) "
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


    def get_submissions_count(self, tag : str) -> int:
        "Returns the number of submissions associated with the research group"
        query = (
            "MATCH (rg:ResearchGroup {tag : $tag})<-[:MEMBER_OF]-(u:User)-[:CREATED|COLLABORATES]->(s:Submission) "
            "RETURN count(s) "
        )
        
        r = self._driver.execute_query(query, tag = tag, routing_= "r", result_transformer_=Result.value)
        if len(r) == 0:  return 0
        return r[0]
    
    
    def get_submission_tags(self, tags : List[str]) -> List[str]:
        "Returns the submission tags associated with the research groups"
        query = (
            "MATCH (rg:ResearchGroup) <-[:MEMBER_OF]-(u:User)-[:CREATED]->(s:Submission) "
            "WHERE rg.tag IN $tags "
            "RETURN s.tag order by s.created_at desc "
        )
        
        r = self._driver.execute_query(query, tags = tags, routing_= "r", result_transformer_=Result.value)
        if len(r) == 0:  return []
        return r
    
    def get_samples_count(self, tag : str) -> int:
        "Returns the number of samples associated with the research group"
        query = (
            "MATCH (rg:ResearchGroup {tag : $tag})<-[:MEMBER_OF]-(u:User)-[:CREATED]->(s:Submission)-[:HAS_SAMPLE]->(sa:Sample) "
            "RETURN count(sa) "
        )
        
        r = self._driver.execute_query(query, tag = tag, routing_= "r", result_transformer_=Result.value)
        if len(r) == 0:  return 0
        return r[0]

    def get_tags(self, limit : int = 40) -> List[str]:
        "Returns the tags of the research groups, ordered by creation date"
        
        query = (
            "MATCH (rg:ResearchGroup) "
            "RETURN rg.tag ORDER BY rg.created_at DESC LIMIT $limit"
        )
        
        r = self._driver.execute_query(query, routing_="r", result_transformer_=Result.value, limit=limit)
        return r 
    
    def get_users(self, tag : str) -> List[str]:
        "Returns the user tags that are part of the research group"
        query = (
            "MATCH (rg:ResearchGroup {tag : $tag})<-[r:MEMBER_OF]-(u:User) "
            "RETURN collect(u.tag) "
        )
        
        r = self._driver.execute_query(query, tag = tag, routing_= "r", result_transformer_=Result.value)
        if len(r) == 0:  return []
        return r[0]
        
        
    def get_users_count(self, tag : str) -> int:
        "Returns the number of users that are part of the research group"
        query = (
            "MATCH (rg:ResearchGroup {tag : $tag})<-[r:MEMBER_OF]-(u:User) "
            "RETURN count(u) "
        )
        
        r = self._driver.execute_query(query, tag = tag, routing_= "r", result_transformer_=Result.value)
        if len(r) == 0:  return 0
        return r[0]
    
    def insert(self, tag : str, research_group : ResearchGroupInput):
        "" 
        if self.exists(tag): raise ValueError("Tag exists already. Delete first or use the update function.")
        
        query = (
            "MERGE (rg:ResearchGroup {tag : $tag}) "
            "ON CREATE "
            "SET rg.created_at = timestamp(), rg.text =  $research_group.text, rg.abbreviation =  $research_group.abbreviation, "
            "rg.address =  $research_group.address, rg.email =  $research_group.email, rg.institute =  $research_group.institute, rg.url =  $research_group.url, "   
            "rg.profile_text =  $research_group.profile_text "
            "ON MATCH "
            "SET rg.modified_at = timestamp(), rg.text =  $research_group.text, rg.abbreviation =  $research_group.abbreviation, "
            "rg.address =  $research_group.address, rg.email =  $research_group.email, rg.institute =  $research_group.institute, rg.url =  $research_group.url, "   
            "rg.profile_text =  $research_group.profile_text "
            "RETURN rg.tag"
        )
        
        r = self._driver.execute_query(query, routing_="w", tag = tag, research_group = research_group.model_dump(exclude_none=True), result_transformer_=Result.value)
        return True if len(r) > 0 else False
        
    def remove_users(self, tag : str, user_tags): 

        if not self.exists(tag): raise ValueError("Research group with tag {tag} does not exist.")
        
        query = (
            "MATCH (rg:ResearchGroup {tag : $tag}) "
            "UNWIND $user_tags as user_tag "
            "MATCH (u:User {tag : user_tag}) "
            "MATCH (rg)<-[r:MEMBER_OF]-(u) "
            "DELETE r"
        )
        
        self._driver.execute_query(query, routing_="w", tag = tag, user_tags = user_tags)
        
        
        
    def update(self, research_group : ResearchGroupInput):
        "" 
        self.insert(research_group)


    def set_subgroup(self, parent_tag : str, child_tag : str):
        "Defines a parent-child relationship between two research groups, where the child group is a subgroup of the parent group."
        if not self.exists(parent_tag): raise ValueError(f"Parent research group with tag {parent_tag} does not exist.")
        if not self.exists(child_tag): raise ValueError(f"Child research group with tag {child_tag} does not exist.")
        
        query = (
            "MATCH (parent:ResearchGroup {tag : $parent_tag}) "
            "MATCH (child:ResearchGroup {tag : $child_tag}) "
            "MERGE (child)-[:SUBGROUP_OF]->(parent) "
        )
        
        self._driver.execute_query(query, routing_="w", parent_tag = parent_tag, child_tag = child_tag)
        
    def remove_subgroup(self, parent_tag : str, child_tag : str):
        "Removes the parent-child relationship between two research groups."
        if not self.exists(parent_tag): raise ValueError(f"Parent research group with tag {parent_tag} does not exist.")
        if not self.exists(child_tag): raise ValueError(f"Child research group with tag {child_tag} does not exist.")
        
        query = (
            "MATCH (parent:ResearchGroup {tag : $parent_tag})<-[r:SUBGROUP_OF]-(child:ResearchGroup {tag : $child_tag}) "
            "DELETE r"
        )
        
        self._driver.execute_query(query, routing_="w", parent_tag = parent_tag, child_tag = child_tag)
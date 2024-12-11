from typing import List
from neo4j import Driver, Result
from lib.data.database.abstract.Timeline import TimelineABC
from config.models.timeline import TimelineModel, TimelineInputModel




class Neo4JTimeline(TimelineABC):
    
    
    def __init__(self,  driver : Driver) -> None:
        self._driver = driver 
        
    def get(self, tags : List[str] = None) -> List[TimelineModel]:
        
        
        query = (
            "MATCH (u:User)-[:CREATED]->(t:Timeline)-[:HAS_CONTENT]->(c:Content) "
        )
        
        if tags is not None and isinstance(tags,list) and len(tags) > 0:
            query += "WHERE t.tag in $tags "
        
        query += "MATCH (submission:Submission)-[:HAS_EVENT]->(t) "
        
        query += (
            "RETURN t.tag as tag, c.content as content, "
            "t.submission_state as submission_state, "
            "t.created_at as created_at, " 
            "u.tag as user_tag, "
            "submission.tag as submission_tag ORDER BY t.created")
        
        r = self._driver.execute_query(query, tags=tags, routing="r", result_transformer_=Result.data)
        return [TimelineModel(**ri) for ri in r]
        
    def exists(self, tag: str) -> bool:
        """Neo4j Implementation to check if a 
        timeline tag exists. 

        Parameters
        ----------
        tag : str
            The timeline tag 

        Returns
        -------
        bool
            If the tag is associated with a tag.

        Raises
        ------
        ValueError
            _description_
        """
        if tag is None or not isinstance(tag,str):
            raise ValueError("Tag must be not None and a string")
    
        
        query = (
            "WITH EXISTS {(t:Timeline {tag : $tag})} as timeline_exists "
            "RETURN timeline_exists "
            )
        
        r = self._driver.execute_query(query, routing_="r", result_transformer_=Result.value, tag = tag)
        return r[0]
        
    def get_timeline_by_submission_tag(self, submission_tag: str)-> List[TimelineModel]:
        ""
        query = (
            "MATCH (submission:Submission) "
            "WHERE submission.tag = $submission_tag "
            "MATCH (submission)-[:HAS_EVENT]->(t:Timeline)-[:HAS_CONTENT]->(c:Content) "
            "MATCH (u:User)-[:CREATED]->(t) "
            "RETURN t.tag as tag, "
            "   c.content as content, "
            "   submission.tag as submission_tag, "
            "   t.submission_state as submission_state, "
            "   t.created_at as created_at, "
            "   u.tag as user_tag ORDER BY t.created_at "
        )
        r = self._driver.execute_query(query, submission_tag = submission_tag, routing="r", result_transformer_=Result.data)
        return [TimelineModel(**ri) for ri in r]
        
    
    def insert(self, timeline : TimelineInputModel):
        "Insert a timeline event to the neo4j database"
        
        query = (
            "MATCH (u:User) "
            "WHERE u.tag = $timeline.user_tag "
            "MATCH (submission:Submission) "
            "WHERE submission.tag = $timeline.submission_tag "
            "WITH u, submission "
            "MERGE (t:Timeline {tag : $timeline.tag}) "
            "ON CREATE "
            "SET t.created_at = timestamp(), t.submission_state = $timeline.submission_state "
            "ON MATCH "
            "SET t.modified_at = timestamp(), t.submission_state = $timeline.submission_state "
            "MERGE (u)-[:CREATED]->(t) "
            "MERGE (c:Content {tag: $timeline.tag}) "
            "ON CREATE "
            "SET c.created_at = timestamp(), c.content = $timeline.content "
            "ON MATCH "
            "SET c.modified_at = timestamp(), c.content = $timeline.concent "
            "MERGE (c)<-[:HAS_CONTENT]-(t)"
            "MERGE (submission)-[:HAS_EVENT]->(t) "
        )
        
        
        self._driver.execute_query(query, routing_="w", timeline = timeline.model_dump())
    
        
    def delete(self, tag: str) -> bool:
        return super().delete(tag)

    def update(self, tag: str):
        return super().update(tag)
        
        
        
        
        
        
        
        
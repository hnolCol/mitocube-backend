

from neo4j import Driver, Result
from typing import List 
from lib.database.abstract.Metatext import MetaTextABC

from services.encryption import create_hierarchical_hash


class Neo4JMetaText(MetaTextABC):
    
    def __init__(self, driver : Driver) -> None:
        self._driver = driver 


    def exists(self, tag : str) -> bool:
        
        query = "WITH EXISTS {(m:MetaText {tag : $tag})} as exists RETURN exists"
        r = self._driver.execute_query(query, routing_="r", tag=tag,
                                        result_transformer_=Result.value)   
        return r[0] if len(r) > 0 else False
    
    def insert(self, title : str, text : str, submission_tag : str, user_tag : str) -> bool:
        "Inserts a new meta text for the given submission. The tag is generated based on the title, submission tag and text." 
        print(title, text, submission_tag, user_tag)
        metatext_tag = create_hierarchical_hash([title,submission_tag,text])
        if self.exists(tag = metatext_tag):
            raise ValueError("Tag is already in the database.")
        
        query = (
            "MATCH (s:Submission {tag : $submission_tag}) "
            "MATCH (u:User {tag : $user_tag}) "
            "MERGE (m:MetaText {tag : $tag}) "
            "SET m.title = $title, m.text = $text, m.created_at = timestamp() "
            "MERGE (s)-[:HAS_METATEXT]->(m) "
            "MERGE (u)-[:CREATED]->(m) "
            "RETURN m.tag as tag"
        )
        r = self._driver.execute_query(query, routing_="w", submission_tag = submission_tag, title = title, text = text, tag = metatext_tag, user_tag = user_tag, result_transformer_=Result.value)
        return True if len(r) > 0 and r[0] is not None else False

    def get(self, tag : str) -> str:
        "Returns the meta text identified by the given tag."
        
        query = (
            "MATCH (m:MetaText {tag : $tag}) "
            "MATCH (m)-[:CREATED]-(u:User) "
            "OPTIONAL MATCH (m)-[:UPDATED]-(u2:User) "
            "RETURN {title: m.title, text: m.text, tag: m.tag, created_at: m.created_at, updated_at : m.updated_at, created_by: u.tag, updated_by: u2.tag} as metatext"
        )
        r = self._driver.execute_query(query, routing_="r", tag=tag, result_transformer_=Result.value)
        if len(r) == 0 or r[0] is None:
            raise KeyError(f"The tag {tag} is not associated with a metatext.")

        return r[0]
    
    
    def get_submission_tag(self, tag : str) -> str:
        "Returns the submission tag associated with the given metatext tag."
        
        query = (
            "MATCH (s:Submission)-[:HAS_METATEXT]->(m:MetaText {tag : $tag}) "
            "RETURN s.tag as submission_tag"
        )
        r = self._driver.execute_query(query, routing_="r", tag=tag, result_transformer_=Result.value)
        if len(r) == 0 or r[0] is None:
            raise KeyError(f"The tag {tag} is not associated with a metatext.")

        return r[0] 
    
    
    def find(self, submission_tag : str = None) -> List[str]:
        """Returns the tags of metatexts. If submission_tag is provided, only metatexts associated with the given submission are returned.
        The tags are sorted by creation date, most recent last.
        Parameters
        ----------
        submission_tag : str, optional
            The tag of the submission to filter metatexts, by default None (all metatexts).

        Returns
        -------
        List[str]
            A list of metatext tags.
        """
        
        if submission_tag is not None:
            query = (
                "MATCH (s:Submission {tag : $submission_tag})-[:HAS_METATEXT]->(m:MetaText) "
                "RETURN m.tag as tag"
            )
        else:
            query = (
                "MATCH (m:MetaText) "
                "RETURN m.tag as tag ORDER BY m.created_at ASC " 
            )
        r = self._driver.execute_query(query, routing_="r", result_transformer_=Result.value, submission_tag = submission_tag)
        return r if len(r) > 0 else []
    
    def update(self, tag : str, user_tag : str, title : str = None, text : str = None) -> bool: 
        "Updates the meta text identified by the given tag."
        
        if not self.exists(tag = tag):
            raise KeyError(f"The tag {tag} is not associated with a metatext.")
        
        query = (
            "MATCH (m:MetaText {tag : $tag}) "
            "SET m += $props, m.updated_at = timestamp() "
            "WITH m "
            "MATCH (u:User {tag : $user_tag}) "
            "MERGE (u)-[:UPDATED]->(m) "
            "RETURN m.tag as tag"
        )
        props = {}
        if title is not None:
            props["title"] = title
        if text is not None:
            props["text"] = text

        r = self._driver.execute_query(query, routing_="w", tag=tag, props=props, user_tag=user_tag, result_transformer_=Result.value)
        return True if len(r) > 0 and r[0] is not None else False
    
    
    def delete(self, tag : str) -> bool:
        "Deletes the meta text identified by the given tag."
        
        if not self.exists(tag = tag):
            raise KeyError(f"The tag {tag} is not associated with a metatext.")
        
        query = (
            "MATCH (m:MetaText {tag : $tag}) "
            "DETACH DELETE m "
        )
        try:
            r = self._driver.execute_query(query, routing_="w", tag=tag, result_transformer_=Result.value)

        except Exception as e:
            print(f"Error deleting metatext with tag {tag}: {e}")
            return False

        return True
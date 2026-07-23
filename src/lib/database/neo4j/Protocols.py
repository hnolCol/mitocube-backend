

from lib.database.abstract.Protocols import ProtocolsABC
from neo4j import Driver, Result 
from typing import List
from services.encryption import create_hierarchical_hash
from config.models.protocols import ProtocolBaseModel

class Neo4JProtocols(ProtocolsABC):

    def __init__(self, driver: Driver) -> None:
        self._driver = driver

    def exists(self, tag: str) -> bool:

        query = "WITH EXISTS {(p:Protocol {tag : $tag})} as exists RETURN exists"
        r = self._driver.execute_query(query, routing_="r", tag=tag,
                                        result_transformer_=Result.value)
        return r[0] if len(r) > 0 else False

    def insert(self, title: str, protocol_text: str, user_tag: str, doi : str = None, pubmed_id : str = None, url : str = None, ignore_exists_error: bool = False) -> bool:
        "Inserts a new protocol. The tag is generated based on the title and protocol text."

        protocol_tag = create_hierarchical_hash([title, protocol_text])
        if self.exists(tag=protocol_tag):
            if ignore_exists_error:
                return False
            raise ValueError("Tag is already in the database.")

        query = (
            "MATCH (u:User {tag : $user_tag}) "
            "MERGE (p:Protocol {tag : $tag}) "
            "SET p.created_at = timestamp(),  p += $props "
            "MERGE (u)-[:CREATED]->(p) "
            "RETURN p.tag as tag"
        )
        
        props = {}
        props["title"] = title
        props["text"] = protocol_text
        
        if doi is not None:
            props["doi"] = doi
        if pubmed_id is not None:
            props["pubmed_id"] = pubmed_id
        if url is not None:
            props["url"] = url
            
        r = self._driver.execute_query(query, routing_="w", title=title, text=protocol_text, tag=protocol_tag, user_tag=user_tag, result_transformer_=Result.value, props=props)
        return True if len(r) > 0 and r[0] is not None else False

    def get(self, tag: str) -> ProtocolBaseModel:
        "Returns the protocol identified by the given tag."

        query = (
            "MATCH (p:Protocol {tag : $tag}) "
            "MATCH (p)<-[:CREATED]-(u:User) "
            "OPTIONAL MATCH (p)<-[:UPDATED]-(u2:User) "
            "WITH p, u, collect(u2.tag) as modified_user_tags "
            "RETURN {title: p.title, text: p.text, tag: p.tag, created_at: p.created_at, modified_at : p.modified_at, user_tag: u.tag, modified_user_tags: modified_user_tags} as protocol"
        )
        r = self._driver.execute_query(query, routing_="r", tag=tag, result_transformer_=Result.value)
        if len(r) == 0 or r[0] is None:
            raise KeyError(f"The tag {tag} is not associated with a protocol.")

        return ProtocolBaseModel(**r[0])

    def get_submissions(self, tag: str) -> List[str]:
        "Returns the submission tags linked to the given protocol tag."

        if not self.exists(tag=tag):
            raise KeyError(f"The tag {tag} is not associated with a protocol.")

        query = (
            "MATCH (s:Submission)-[:USES_PROTOCOL]->(p:Protocol {tag : $tag}) "
            "RETURN s.tag as submission_tag"
        )
        r = self._driver.execute_query(query, routing_="r", tag=tag, result_transformer_=Result.value)
        return r if len(r) > 0 else []

    def find(self, search_string : str = None, submission_tags: List[str] = None, limit : int = None) -> List[str]:
        """Returns the tags of protocols. If submission_tag is provided, only protocols linked to the given submission are returned.
        The tags are sorted by creation date, most recent last.
        Parameters
        ----------
        search_string : str, optional
            A string to search for in protocol titles, by default None.
        submission_tags : List[str], optional
            The tags of the submissions to filter protocols, by default None (all protocols).

        Returns
        -------
        List[str]
            A list of protocol tags.
        """

        if submission_tags is not None:
            query = (
                "MATCH (s:Submission) WHERE s.tag IN $submission_tags "
                "MATCH (s)-[:USES_PROTOCOL]->(p:Protocol) "
                "RETURN p.tag as tag ORDER BY p.created_at ASC "
                + (f" LIMIT {limit}" if limit is not None else "")
            )
        else:
            query = (
                "MATCH (p:Protocol) "
                "WHERE $search_string IS NULL OR (lower(p.title) CONTAINS $search_string OR lower(p.text) CONTAINS $search_string) "
                "RETURN p.tag as tag ORDER BY p.created_at ASC "
                + (f" LIMIT {limit}" if limit is not None else "")
            )
        r = self._driver.execute_query(query, routing_="r", result_transformer_=Result.value, submission_tags=submission_tags, search_string=search_string.lower() if search_string is not None else None)
        return r if len(r) > 0 else []

    def update(self, tag: str, user_tag: str, title: str = None, protocol_text: str = None, doi: str = None, pubmed_id: str = None, url: str = None) -> bool:
        "Updates the protocol identified by the given tag."

        if not self.exists(tag=tag):
            raise KeyError(f"The tag {tag} is not associated with a protocol.")

        query = (
            "MATCH (p:Protocol {tag : $tag}) "
            "SET p += $props, p.modified_at = timestamp() "
            "WITH p "
            "MATCH (u:User {tag : $user_tag}) "
            "MERGE (u)-[:UPDATED]->(p) "
            "RETURN p.tag as tag"
        )
        props = {}
        if title is not None:
            props["title"] = title
        if protocol_text is not None:
            props["text"] = protocol_text
        if doi is not None:
            props["doi"] = doi
        if pubmed_id is not None:
            props["pubmed_id"] = pubmed_id
        if url is not None:
            props["url"] = url

        r = self._driver.execute_query(query, routing_="w", tag=tag, props=props, user_tag=user_tag, result_transformer_=Result.value)
        return True if len(r) > 0 and r[0] is not None else False

    def link(self, tag: str, submission_tag: str, user_tag: str, ignore_exists_error: bool = False) -> bool:
        "Links an existing protocol to a submission."

        if not self.exists(tag=tag):
            raise KeyError(f"The tag {tag} is not associated with a protocol.")

        check_query = (
            "WITH EXISTS {(s:Submission {tag : $submission_tag})-[:USES_PROTOCOL]->(p:Protocol {tag : $tag})} as exists "
            "RETURN exists"
        )
        already_linked = self._driver.execute_query(check_query, routing_="r", tag=tag, submission_tag=submission_tag,
                                                      result_transformer_=Result.value)
        if len(already_linked) > 0 and already_linked[0]:
            if ignore_exists_error:
                return False
            raise ValueError("The protocol is already linked to this submission.")

        query = (
            "MATCH (s:Submission {tag : $submission_tag}) "
            "MATCH (p:Protocol {tag : $tag}) "
            "MATCH (u:User {tag : $user_tag}) "
            "MERGE (s)-[r:USES_PROTOCOL]->(p) "
            "SET r.created_at = timestamp(), r.user_tag = $user_tag "
            "RETURN p.tag as tag"
        )
        r = self._driver.execute_query(query, routing_="w", submission_tag=submission_tag, tag=tag, user_tag=user_tag, result_transformer_=Result.value)
        return True if len(r) > 0 and r[0] is not None else False

    def is_linked(self, tag: str, submission_tag: str) -> bool:
        "Checks if a protocol is linked to a submission."

        if not self.exists(tag=tag):
            raise KeyError(f"The tag {tag} is not associated with a protocol.")

        query = (
            "WITH EXISTS {(s:Submission {tag : $submission_tag})-[:USES_PROTOCOL]->(p:Protocol {tag : $tag})} as exists "
            "RETURN exists"
        )
        r = self._driver.execute_query(query, routing_="r", tag=tag, submission_tag=submission_tag,
                                        result_transformer_=Result.value)
        return r[0] if len(r) > 0 else False

    def unlink(self, tag: str, submission_tag: str) -> bool:
        "Unlinks a protocol from a submission."

        if not self.exists(tag=tag):
            raise KeyError(f"The tag {tag} is not associated with a protocol.")

        is_linked = self.is_linked(tag=tag, submission_tag=submission_tag)
        if not is_linked:
            raise ValueError("The protocol is not linked to this submission.")

        query = (
            "MATCH (s:Submission {tag : $submission_tag})-[r:USES_PROTOCOL]->(p:Protocol {tag : $tag}) "
            "DELETE r "
            "RETURN p.tag as tag"
        )
        r = self._driver.execute_query(query, routing_="w", submission_tag=submission_tag, tag=tag, result_transformer_=Result.value)
        return True if len(r) > 0 and r[0] is not None else False

    def delete(self, tag: str) -> bool:
        "Deletes the protocol identified by the given tag."

        if not self.exists(tag=tag):
            raise KeyError(f"The tag {tag} is not associated with a protocol.")

        query = (
            "MATCH (p:Protocol {tag : $tag}) "
            "DETACH DELETE p "
        )
        try:
            r = self._driver.execute_query(query, routing_="w", tag=tag, result_transformer_=Result.value)

        except Exception as e:
            print(f"Error deleting protocol with tag {tag}: {e}")
            return False

        return True
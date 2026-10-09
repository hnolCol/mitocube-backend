from typing import List
from neo4j import Driver, Result

from lib.database.abstract.Consortium import ConsortiumABC
from config.models.consortium import ConsortiumInput, ConsortiumModel


class Neo4JConsortium(ConsortiumABC):

    def __init__(self, driver : Driver) -> None:
        self._driver = driver

    def exists(self, tag : str) -> bool:
        query = (
            "WITH EXISTS {(c:Consortium {tag : $tag})} as consortium_exists "
            "RETURN consortium_exists "
        )
        r = self._driver.execute_query(query, tag = tag, result_transformer_=Result.value)
        return r[0]

    def insert(self, tag : str, consortium : ConsortiumInput) -> bool:
        """Creates or updates a consortium. The tag is expected to be a unique hash of the content."""
        query = (
            "MERGE (c:Consortium {tag : $tag}) "
            "ON CREATE "
            "SET c.created_at = timestamp(), c.text = $consortium.text, c.abbreviation = $consortium.abbreviation, "
            "c.email = $consortium.email, c.profile_text = $consortium.profile_text, c.url = $consortium.url "
            "ON MATCH "
            "SET c.modified_at = timestamp(), c.text = $consortium.text, c.abbreviation = $consortium.abbreviation, "
            "c.email = $consortium.email, c.profile_text = $consortium.profile_text, c.url = $consortium.url "
            "RETURN c.tag"
        )
        r = self._driver.execute_query(query, routing_="w", tag = tag,
                                       consortium = consortium.model_dump(exclude_none=True),
                                       result_transformer_=Result.value)
        return True if len(r) > 0 else False

    def get(self, tag : str) -> ConsortiumModel:
        query = (
            "MATCH (c:Consortium) "
            "WHERE c.tag = $tag "
            "RETURN properties(c) "
        )
        r = self._driver.execute_query(query, routing_="r", result_transformer_=Result.value, tag = tag)
        return ConsortiumModel(**r[0]) if len(r) > 0 else None

    def delete(self, tag : str) -> bool:
        """Deletes a consortium together with its membership and sharing relations."""
        query = (
            "MATCH (c:Consortium {tag : $tag}) "
            "DETACH DELETE c "
            "RETURN count(c) "
        )
        r = self._driver.execute_query(query, routing_="w", tag = tag, result_transformer_=Result.value)
        return r[0] > 0

    def find(self, search_string : str = None, group_tags : List[str] = None, limit : int = 40) -> List[str]:
        """Finds consortium tags that match the search string or contain the given research groups."""
        if group_tags is not None:
            query = (
                "MATCH (c:Consortium)<-[:MEMBER_OF]-(rg:ResearchGroup) "
                "WHERE rg.tag IN $group_tags "
            )
        else:
            query = (
                "MATCH (c:Consortium) "
                "WHERE true "
            )

        if search_string is not None and search_string != "":
            query += "AND (toLower(c.text) CONTAINS $search_string OR toLower(c.abbreviation) CONTAINS $search_string OR toLower(c.tag) CONTAINS $search_string) "

        query += "RETURN DISTINCT c.tag as tag "

        if limit is not None:
            query += "LIMIT $limit"

        r = self._driver.execute_query(
            query,
            routing_="r",
            result_transformer_=Result.value,
            search_string=search_string.lower() if search_string is not None else None,
            group_tags=group_tags,
            limit=limit
        )
        return r

    def get_tags(self, limit : int = 40) -> List[str]:
        """Returns the tags of all consortiums, ordered by creation date"""
        query = (
            "MATCH (c:Consortium) "
            "RETURN c.tag ORDER BY c.created_at DESC LIMIT $limit"
        )
        r = self._driver.execute_query(query, routing_="r", limit=limit, result_transformer_=Result.value)
        return r

    def get_groups(self, tag : str) -> List[str]:
        """Returns the research group tags that are members of the consortium"""
        query = (
            "MATCH (c:Consortium {tag : $tag})<-[r:MEMBER_OF]-(rg:ResearchGroup) "
            "RETURN collect(rg.tag) "
        )
        r = self._driver.execute_query(query, tag = tag, routing_="r", result_transformer_=Result.value)
        return r[0] if len(r) > 0 else []

    def insert_groups(self, tag : str, group_tags : List[str]):
        """Adds research groups to the consortium"""
        if not self.exists(tag): raise ValueError(f"Consortium with tag {tag} does not exist.")

        query = (
            "MATCH (c:Consortium {tag : $tag}) "
            "UNWIND $group_tags as group_tag "
            "MATCH (rg:ResearchGroup {tag : group_tag}) "
            "MERGE (c)<-[r:MEMBER_OF]-(rg) "
            "ON CREATE "
            "SET r.created_at = timestamp() "
        )
        self._driver.execute_query(query, routing_="w", tag = tag, group_tags = group_tags)

    def remove_groups(self, tag : str, group_tags : List[str]):
        """Removes research groups from the consortium"""
        if not self.exists(tag): raise ValueError(f"Consortium with tag {tag} does not exist.")

        query = (
            "MATCH (c:Consortium {tag : $tag}) "
            "UNWIND $group_tags as group_tag "
            "MATCH (rg:ResearchGroup {tag : group_tag}) "
            "MATCH (c)<-[r:MEMBER_OF]-(rg) "
            "DELETE r"
        )
        self._driver.execute_query(query, routing_="w", tag = tag, group_tags = group_tags)

    def get_submission_tags(self, tag : str) -> List[str]:
        """Returns the submission tags that are shared with the consortium"""
        query = (
            "MATCH (c:Consortium {tag : $tag})<-[r:SHARED_WITH]-(s:Submission) "
            "RETURN s.tag ORDER BY s.created_at DESC "
        )
        r = self._driver.execute_query(query, tag = tag, routing_="r", result_transformer_=Result.value)
        return r

    def share_submission(self, consortium_tag : str, submission_tag : str) -> bool:
        """Shares a submission with the consortium"""
        if not self.exists(consortium_tag): raise ValueError(f"Consortium with tag {consortium_tag} does not exist.")

        query = (
            "MATCH (c:Consortium {tag : $consortium_tag}), (s:Submission {tag : $submission_tag}) "
            "MERGE (s)-[r:SHARED_WITH]->(c) "
            "ON CREATE "
            "SET r.created_at = timestamp() "
            "RETURN count(r) "
        )
        r = self._driver.execute_query(query, routing_="w",
                                       consortium_tag = consortium_tag,
                                       submission_tag = submission_tag,
                                       result_transformer_=Result.value)
        return r[0] > 0

    def unshare_submission(self, consortium_tag : str, submission_tag : str) -> bool:
        """Removes a submission from the consortium"""
        query = (
            "MATCH (s:Submission {tag : $submission_tag})-[r:SHARED_WITH]->(c:Consortium {tag : $consortium_tag}) "
            "DELETE r "
            "RETURN count(r) "
        )
        r = self._driver.execute_query(query, routing_="w",
                                       consortium_tag = consortium_tag,
                                       submission_tag = submission_tag,
                                       result_transformer_=Result.value)
        return r[0] > 0

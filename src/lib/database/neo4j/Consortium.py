from typing import List, Dict
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

    def find(self, search_string : str = None, group_tags : List[str] = None, user_tags : List[str] = None, limit : int = 40) -> List[str]:
        """Finds consortium tags that match the search string, contain the given research groups or that the given users research groups belong to."""
        if user_tags is not None:
            query = (
                "MATCH (c:Consortium)<-[:MEMBER_OF]-(rg:ResearchGroup)<-[:MEMBER_OF]-(u:User) "
                "WHERE u.tag IN $user_tags "
            )
            if group_tags is not None:
                query += "AND rg.tag IN $group_tags "
        elif group_tags is not None:
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
            user_tags=user_tags,
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

    def get_user_tags(self, tag : str) -> List[str]:
        """Returns the user tags of all users that are members of the consortiums research groups"""
        query = (
            "MATCH (c:Consortium {tag : $tag})<-[:MEMBER_OF]-(rg:ResearchGroup)<-[:MEMBER_OF]-(u:User) "
            "RETURN DISTINCT u.tag ORDER BY u.tag "
        )
        r = self._driver.execute_query(query, tag = tag, routing_="r", result_transformer_=Result.value)
        return r

    def find_by_user(self, user_tag : str, limit : int = 40) -> List[str]:
        """Returns the tags of all consortiums the users research groups are member of"""
        query = (
            "MATCH (u:User {tag : $user_tag})-[:MEMBER_OF]->(rg:ResearchGroup)-[:MEMBER_OF]->(c:Consortium) "
            "RETURN DISTINCT c.tag ORDER BY c.created_at DESC "
        )
        if limit is not None:
            query += "LIMIT $limit"
        r = self._driver.execute_query(query, routing_="r", user_tag = user_tag, limit = limit, result_transformer_=Result.value)
        return r

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
        from lib.cache.scope_cache import invalidate_all_cached_scopes
        invalidate_all_cached_scopes()  # shares affect the scope of all consortium member group users

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
        from lib.cache.scope_cache import invalidate_all_cached_scopes
        invalidate_all_cached_scopes()  # shares affect the scope of all consortium member group users

    def get_submission_tags(self, tag : str) -> List[str]:
        """Returns the submission tags that are shared with the consortium"""
        query = (
            "MATCH (c:Consortium {tag : $tag})<-[r:SHARED_WITH]-(s:Submission) "
            "WHERE r.status = 'approved' "
            "RETURN s.tag ORDER BY s.created_at DESC "
        )
        r = self._driver.execute_query(query, tag = tag, routing_="r", result_transformer_=Result.value)
        return r

    def share_submission(self, consortium_tag : str, submission_tag : str, user_tag : str, approved : bool = False) -> bool:
        """Shares a submission with the consortium. If approved is False, the share request is
        created with status pending and requires the approval of a research group head (PI)."""
        if not self.exists(consortium_tag): raise ValueError(f"Consortium with tag {consortium_tag} does not exist.")

        status = "approved" if approved else "pending"
        query = (
            "MATCH (c:Consortium {tag : $consortium_tag}), (s:Submission {tag : $submission_tag}) "
            "MERGE (s)-[r:SHARED_WITH]->(c) "
            "ON CREATE "
            "SET r.created_at = timestamp(), r.status = $status, r.requested_by = $user_tag "
            "ON MATCH "
            "SET r.modified_at = timestamp() "
            "RETURN count(r) "
        )
        r = self._driver.execute_query(query, routing_="w",
                                       consortium_tag = consortium_tag,
                                       submission_tag = submission_tag,
                                       status = status,
                                       user_tag = user_tag,
                                       result_transformer_=Result.value)
        return r[0] > 0
        from lib.cache.scope_cache import invalidate_all_cached_scopes
        invalidate_all_cached_scopes()  # shares affect the scope of all consortium member group users

    def get_pending_share_requests_for_head(self, user_tag : str) -> List[Dict]:
        """Returns the pending share requests that the given research group head (PI) can approve.
        A head sees the requests of the users that are members of the research groups they lead."""
        query = (
            "MATCH (pi:User {tag : $user_tag})-[:HEAD_OF]->(rg:ResearchGroup)<-[:MEMBER_OF]-(owner:User) "
            "MATCH (owner)-[:CREATED]->(s:Submission)-[r:SHARED_WITH]->(c:Consortium) "
            "WHERE r.status = 'pending' "
            "RETURN s.tag AS submission_tag, c.tag AS consortium_tag, r.requested_by AS requested_by, r.created_at AS created_at "
            "ORDER BY r.created_at DESC "
        )
        r = self._driver.execute_query(query, routing_="r", user_tag = user_tag, result_transformer_=Result.data)
        return list(r) if r else []

    def approve_share_request(self, consortium_tag : str, submission_tag : str, user_tag : str) -> bool:
        """Approves a pending share request, making the submission accessible to the consortium"""
        query = (
            "MATCH (s:Submission {tag : $submission_tag})-[r:SHARED_WITH]->(c:Consortium {tag : $consortium_tag}) "
            "WHERE r.status = 'pending' "
            "SET r.status = 'approved', r.approved_by = $user_tag, r.approved_at = timestamp() "
            "RETURN count(r) "
        )
        r = self._driver.execute_query(query, routing_="w",
                                       consortium_tag = consortium_tag,
                                       submission_tag = submission_tag,
                                       user_tag = user_tag,
                                       result_transformer_=Result.value)
        return r[0] > 0
        from lib.cache.scope_cache import invalidate_all_cached_scopes
        invalidate_all_cached_scopes()  # shares affect the scope of all consortium member group users

    def deny_share_request(self, consortium_tag : str, submission_tag : str) -> bool:
        """Denies a pending share request, removing the pending relation"""
        query = (
            "MATCH (s:Submission {tag : $submission_tag})-[r:SHARED_WITH]->(c:Consortium {tag : $consortium_tag}) "
            "WHERE r.status = 'pending' "
            "DELETE r "
            "RETURN count(r) "
        )
        r = self._driver.execute_query(query, routing_="w",
                                       consortium_tag = consortium_tag,
                                       submission_tag = submission_tag,
                                       result_transformer_=Result.value)
        return r[0] > 0
        from lib.cache.scope_cache import invalidate_all_cached_scopes
        invalidate_all_cached_scopes()  # shares affect the scope of all consortium member group users

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
        from lib.cache.scope_cache import invalidate_all_cached_scopes
        invalidate_all_cached_scopes()  # shares affect the scope of all consortium member group users

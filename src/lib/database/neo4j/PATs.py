from typing import List, Optional, Tuple

from neo4j import Driver, Result

from config.models.pat import PATResponseModel
from lib.database.abstract.PATs import PATABC, hash_pat_token
from services.random_generators import get_random_string


class Neo4JPATs(PATABC):
    """Neo4J implementation of the personal access token store.

    Graph
    -----
    (:User)-[:HAS_TOKEN]->(:PAT {tag, name, hash, scopes, created_at, expires_at, last_used_at, revoked})
    """

    _RETURN = ("t{.*, "
               "expires_soon: t.expires_at - timestamp() < 604800000} AS pat ")

    def __init__(self, driver : Driver) -> None:
        self._driver = driver
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        self._driver.execute_query(
            "CREATE INDEX pat_hash_index IF NOT EXISTS FOR (t:PAT) ON (t.hash) "
        )

    def _unique_tag(self) -> str:
        tag = f"pat_{get_random_string(8).lower()}"
        while self.exists(tag):
            tag = f"pat_{get_random_string(8).lower()}"
        return tag

    def exists(self, tag : str) -> bool:
        query = "RETURN EXISTS { (:PAT {tag : $tag}) } AS exists "
        r = self._driver.execute_query(query, routing_="r", tag=tag, result_transformer_=Result.value)
        return r[0]

    def create(self, user_tag : str, name : str, scopes : List[str], expires_at_epochmillis : int) -> Tuple[PATResponseModel, str]:
        blocked = self._driver.execute_query(
            "MATCH (u:User {tag : $user_tag}) "
            "RETURN coalesce(u.pat_creation_blocked, false) AS blocked ",
            routing_="r", user_tag=user_tag, result_transformer_=Result.value)
        if len(blocked) == 0:
            raise ValueError(f"User with tag '{user_tag}' not found.")
        if blocked[0]:
            raise ValueError(f"Personal access token creation is blocked for user '{user_tag}'.")
        token = generate_pat_token()
        props = {
            "tag": self._unique_tag(),
            "name": name,
            "hash": hash_pat_token(token),
            "scopes": list(scopes),
            "expires_at": expires_at_epochmillis,
            "revoked": False,
        }
        query = (
            "MATCH (u:User {tag : $user_tag}) "
            "CREATE (t:PAT $props) "
            "SET t.created_at = timestamp(), t.last_used_at = null "
            "CREATE (u)-[:HAS_TOKEN]->(t) "
            "RETURN t{.*, last_used_at: null} AS pat "
        )
        r = self._driver.execute_query(query, routing_="w", user_tag=user_tag, props=props,
                                       result_transformer_=Result.value)
        if len(r) == 0:
            raise ValueError(f"User with tag '{user_tag}' not found.")
        return PATResponseModel(**r[0]), token

    def get_by_hash(self, token_hash : str) -> Optional[dict]:
        query = (
            "MATCH (u:User)-[:HAS_TOKEN]->(t:PAT {hash : $hash}) "
            "WHERE t.revoked = false AND t.expires_at > timestamp() "
            "RETURN u.tag AS user_tag, t{.*, last_used_at: null} AS pat "
        )
        r = self._driver.execute_query(query, routing_="r", hash=token_hash, result_transformer_=Result.data)
        if len(r) == 0:
            return None
        return r[0]

    def list(self, user_tag : str) -> List[PATResponseModel]:
        query = (
            "MATCH (:User {tag : $user_tag})-[:HAS_TOKEN]->(t:PAT) "
            "RETURN t{.*, last_used_at: null} AS pat ORDER BY pat.created_at DESC "
        )
        r = self._driver.execute_query(query, routing_="r", user_tag=user_tag, result_transformer_=Result.value)
        return [PATResponseModel(**p) for p in r]

    def revoke(self, user_tag : str, pat_tag : str) -> bool:
        query = (
            "MATCH (:User {tag : $user_tag})-[:HAS_TOKEN]->(t:PAT {tag : $pat_tag}) "
            "SET t.revoked = true "
            "RETURN count(t) AS n "
        )
        r = self._driver.execute_query(query, routing_="w", user_tag=user_tag, pat_tag=pat_tag,
                                       result_transformer_=Result.value)
        return r[0] > 0

    def revoke_by_admin(self, pat_tag : str, revoked_by : str) -> bool:
        query = (
            "MATCH (t:PAT {tag : $pat_tag}) "
            "WHERE t.revoked = false "
            "SET t.revoked = true, t.revoked_by = $revoked_by, t.revoked_at = timestamp() "
            "RETURN count(t) AS n "
        )
        r = self._driver.execute_query(query, routing_="w", pat_tag=pat_tag, revoked_by=revoked_by,
                                       result_transformer_=Result.value)
        return r[0] > 0

    def set_creation_blocked(self, user_tag : str, blocked : bool) -> bool:
        query = (
            "MATCH (u:User {tag : $user_tag}) "
            "SET u.pat_creation_blocked = $blocked "
            "RETURN count(u) AS n "
        )
        r = self._driver.execute_query(query, routing_="w", user_tag=user_tag, blocked=blocked,
                                       result_transformer_=Result.value)
        return r[0] > 0

    def touch(self, pat_tag : str) -> None:
        query = "MATCH (t:PAT {tag : $pat_tag}) SET t.last_used_at = timestamp() "
        self._driver.execute_query(query, routing_="w", pat_tag=pat_tag)

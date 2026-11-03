from typing import List, Optional

from neo4j import Driver, Result

from lib.database.abstract.Policy import PolicyABC
from config.models.Policy import PolicyModel, PolicyInsertModel, PolicyUpdateModel, PolicyStatusModel


class Neo4JPolicy(PolicyABC):

    def __init__(self, driver : Driver) -> None:
        self._driver = driver

    def list(self) -> List[PolicyModel]:
        "Returns all policies, oldest first."
        query = (
            "MATCH (p:Policy) "
            "RETURN properties(p) ORDER BY p.created_at "
        )
        r = self._driver.execute_query(query, routing_="r", result_transformer_=Result.value)
        return [PolicyModel(**ri) for ri in r]

    def get(self, tag : str) -> Optional[PolicyModel]:
        "Returns the policy with the given tag, or None if it does not exist."
        query = (
            "MATCH (p:Policy {tag : $tag}) "
            "RETURN properties(p) "
        )
        r = self._driver.execute_query(query, routing_="r", tag=tag, result_transformer_=Result.value)
        return PolicyModel(**r[0]) if len(r) > 0 else None

    def create(self, policy : PolicyInsertModel, user_tag : str) -> PolicyModel:
        "Creates a new policy. The tag is generated from the title by PolicyInsertModel."
        if self.get(policy.tag) is not None:
            raise ValueError(f"A policy with the title '{policy.title}' already exists.")
        query = (
            "CREATE (p:Policy {tag : $tag, title : $title, text : $text, required : $required, "
            "    version : 0, created_at : timestamp(), updated_at : timestamp(), updated_by : $user_tag}) "
            "RETURN properties(p) "
        )
        r = self._driver.execute_query(query, routing_="w",
                                       tag=policy.tag,
                                       title=policy.title,
                                       text=policy.text,
                                       required=policy.required,
                                       user_tag=user_tag,
                                       result_transformer_=Result.value)
        return PolicyModel(**r[0])

    def update(self, tag : str, policy : PolicyUpdateModel, user_tag : str) -> Optional[PolicyModel]:
        """Updates the policy. If bump_version is True, the version is increased and all
        users have to agree again (their stored agreement no longer matches the version)."""
        query = (
            "MATCH (p:Policy {tag : $tag}) "
            "SET p.title = $title, p.text = $text, p.required = $required, "
            "    p.updated_at = timestamp(), p.updated_by = $user_tag, "
            "    p.version = CASE WHEN $bump_version THEN p.version + 1 ELSE p.version END "
            "RETURN properties(p) "
        )
        r = self._driver.execute_query(query, routing_="w",
                                       tag=tag,
                                       title=policy.title,
                                       text=policy.text,
                                       required=policy.required,
                                       bump_version=policy.bump_version,
                                       user_tag=user_tag,
                                       result_transformer_=Result.value)
        return PolicyModel(**r[0]) if len(r) > 0 else None

    def delete(self, tag : str) -> bool:
        "Deletes the policy together with all user agreements to it."
        query = (
            "MATCH (p:Policy {tag : $tag}) "
            "WITH p, p.tag AS deleted_tag "
            "DETACH DELETE p "
            "RETURN deleted_tag "
        )
        r = self._driver.execute_query(query, routing_="w", tag=tag, result_transformer_=Result.value)
        return len(r) > 0

    def agree(self, tag : str, user_tag : str) -> bool:
        "Marks the user as agreed to the current version of the policy."
        query = (
            "MATCH (p:Policy {tag : $tag}) "
            "MATCH (u:User {tag : $user_tag}) "
            "MERGE (u)-[a:AGREED_TO]->(p) "
            "SET a.version = p.version, a.at = timestamp() "
            "RETURN true "
        )
        r = self._driver.execute_query(query, routing_="w", tag=tag, user_tag=user_tag, result_transformer_=Result.value)
        return r[0] if len(r) > 0 else False

    def get_status(self, user_tag : str) -> List[PolicyStatusModel]:
        "Returns for every policy whether the user has to agree to it before using MitoCube."
        query = (
            "MATCH (u:User {tag : $user_tag}) "
            "MATCH (p:Policy) "
            "OPTIONAL MATCH (u)-[a:AGREED_TO]->(p) "
            "RETURN p.tag AS tag, p.title AS title, "
            "       coalesce(p.required, false) AS required, "
            "       coalesce(a.version = p.version, false) AS agreed, "
            "       coalesce(p.version, 0) AS version "
            "ORDER BY p.created_at "
        )
        r = self._driver.execute_query(query, routing_="r", user_tag=user_tag, result_transformer_=Result.data)
        return [PolicyStatusModel(**row, must_agree=row["required"] and not row["agreed"]) for row in r]
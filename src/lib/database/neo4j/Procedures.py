import hashlib
import json
import time

from neo4j import Driver, Result
from typing import List, Optional

from lib.database.abstract.Procedures import ModularProceduresABC
from services.encryption import create_hierarchical_hash
from config.models.procedures import (
    ModularProcedureBaseModel,
    ModularProcedureSubmissionModel,
    PublishModularProcedureModel,
)



class Neo4JModularProcedures(ModularProceduresABC):

    def __init__(self, driver: Driver) -> None:
        self._driver = driver

    def _compute_content_hash(self, title: str, description: str,
                               condition_application_tags: List[str],
                               protocol_tags: List[str]) -> str:
        "Computes the SHA-256 hash over the canonical serialization of the procedure content."
        content = {
            "title": title,
            "description": description,
            "condition_application_tags": sorted(condition_application_tags or []),
            "protocol_tags": sorted(protocol_tags or []),
        }
        return hashlib.sha256(json.dumps(content, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()

    def exists(self, tag: str) -> bool:
        query = "WITH EXISTS {(m:ModularProcedure {tag : $tag})} as exists RETURN exists"
        r = self._driver.execute_query(query, routing_="r", tag=tag, result_transformer_=Result.value)
        return r[0] if len(r) > 0 else False

    def insert(self, title: str, description: str, user_tag: str,
               condition_application_tags: List[str] = None,
               protocol_tags: List[str] = None) -> str:
        "Inserts a new draft modular procedure. The tag is generated based on the title and description."
        condition_application_tags = condition_application_tags or []
        protocol_tags = protocol_tags or []
        tag = create_hierarchical_hash([title, description])
        if self.exists(tag=tag):
            raise ValueError("Tag is already in the database.")

        query = (
            "MATCH (u:User {tag : $user_tag}) "
            "MERGE (m:ModularProcedure {tag : $tag}) "
            "SET m.created_at = timestamp(), m += $props "
            "MERGE (u)-[:CREATED]->(m) "
            "RETURN m.tag as tag"
        )

        props = {
            "title": title,
            "description": description,
            "status": "DRAFT",
            "version": 1,
            "user_tag": user_tag,
        }

        r = self._driver.execute_query(query, routing_="w", tag=tag, user_tag=user_tag, props=props,
                                       result_transformer_=Result.value)
        if len(r) == 0 or r[0] is None:
            return None

        for ca_tag in condition_application_tags:
            self._driver.execute_query(
                "MATCH (m:ModularProcedure {tag : $tag}) MATCH (c:ConditionApplication {tag : $ca_tag}) "
                "MERGE (m)-[:HAS_CONDITION_APPLICATION]->(c)",
                routing_="w", tag=tag, ca_tag=ca_tag)

        for protocol_tag in protocol_tags:
            self._driver.execute_query(
                "MATCH (m:ModularProcedure {tag : $tag}) MATCH (p:Protocol {tag : $protocol_tag}) "
                "MERGE (m)-[:HAS_PROTOCOL]->(p)",
                routing_="w", tag=tag, protocol_tag=protocol_tag)

        return r[0]

    def get(self, tag: str) -> ModularProcedureBaseModel:
        "Returns the modular procedure identified by the given tag."
        query = (
            "MATCH (m:ModularProcedure {tag : $tag}) "
            "OPTIONAL MATCH (m)-[:HAS_CONDITION_APPLICATION]->(c:ConditionApplication) "
            "OPTIONAL MATCH (m)-[:HAS_PROTOCOL]->(p:Protocol) "
            "WITH m, collect(DISTINCT c.tag) as ca_tags, collect(DISTINCT p.tag) as protocol_tags "
            "RETURN {tag: m.tag, title: m.title, description: m.description, status: m.status, "
            "version: m.version, content_hash: m.content_hash, user_tag: m.user_tag, "
            "created_at: m.created_at, published_at: m.published_at, "
            "condition_application_tags: ca_tags, protocol_tags: protocol_tags} as procedure"
        )
        r = self._driver.execute_query(query, routing_="r", tag=tag, result_transformer_=Result.data)
        if len(r) == 0:
            raise KeyError("Modular procedure not found.")
        return ModularProcedureBaseModel(**r[0]["procedure"])

    def find(self, search_string: str = None, status: str = None, limit: int = None) -> List[str]:
        "Returns the tags of modular procedures, sorted by creation date, most recent last."
        query = "MATCH (m:ModularProcedure) "
        params = {}
        if search_string is not None:
            query += "WHERE m.title CONTAINS $search_string "
            params["search_string"] = search_string
        if status is not None:
            query += ("AND " if "WHERE" in query else "WHERE ") + "m.status = $status "
            params["status"] = status
        query += "RETURN m.tag as tag ORDER BY m.created_at ASC"
        if limit is not None:
            query += " LIMIT $limit"
            params["limit"] = limit
        r = self._driver.execute_query(query, routing_="r", parameters_=params, result_transformer_=Result.value)
        return r

    def update(self, tag: str, title: str, description: str, user_tag: str,
               condition_application_tags: List[str] = None,
               protocol_tags: List[str] = None) -> bool:
        "Updates a draft modular procedure. Published procedures are immutable."
        if not self.exists(tag=tag):
            raise ValueError("Modular procedure not found.")
        if self.get(tag=tag).status == "PUBLISHED":
            raise ValueError("Published modular procedures are immutable.")
        condition_application_tags = condition_application_tags or []
        protocol_tags = protocol_tags or []

        query = (
            "MATCH (m:ModularProcedure {tag : $tag}) "
            "OPTIONAL MATCH (m)-[r:HAS_CONDITION_APPLICATION]->() DELETE r "
            "WITH DISTINCT m "
            "OPTIONAL MATCH (m)-[r2:HAS_PROTOCOL]->() DELETE r2 "
            "WITH DISTINCT m "
            "SET m.title = $title, m.description = $description, m.modified_at = timestamp() "
            "MERGE (u:User {tag : $user_tag})-[:UPDATED]->(m) "
            "RETURN m.tag as tag"
        )
        r = self._driver.execute_query(query, routing_="w", tag=tag, title=title, description=description,
                                       user_tag=user_tag, result_transformer_=Result.value)
        if len(r) == 0 or r[0] is None:
            return False

        for ca_tag in condition_application_tags:
            self._driver.execute_query(
                "MATCH (m:ModularProcedure {tag : $tag}) MATCH (c:ConditionApplication {tag : $ca_tag}) "
                "MERGE (m)-[:HAS_CONDITION_APPLICATION]->(c)",
                routing_="w", tag=tag, ca_tag=ca_tag)

        for protocol_tag in protocol_tags:
            self._driver.execute_query(
                "MATCH (m:ModularProcedure {tag : $tag}) MATCH (p:Protocol {tag : $protocol_tag}) "
                "MERGE (m)-[:HAS_PROTOCOL]->(p)",
                routing_="w", tag=tag, protocol_tag=protocol_tag)

        return True

    def publish(self, tag: str, user_tag: str) -> PublishModularProcedureModel:
        "Publishes a draft modular procedure: sets the SHA-256 content hash and locks it."
        procedure = self.get(tag=tag)
        if procedure.status == "PUBLISHED":
            raise ValueError("Modular procedure is already published.")
        content_hash = self._compute_content_hash(title=procedure.title, description=procedure.description,
                                                  condition_application_tags=procedure.condition_application_tags,
                                                  protocol_tags=procedure.protocol_tags)
        query = (
            "MATCH (m:ModularProcedure {tag : $tag}) "
            "SET m.status = 'PUBLISHED', m.content_hash = $content_hash, "
            "m.published_at = timestamp() "
            "MERGE (u:User {tag : $user_tag})-[:PUBLISHED]->(m) "
            "RETURN m.version as version"
        )
        r = self._driver.execute_query(query, routing_="w", tag=tag, content_hash=content_hash,
                                       user_tag=user_tag, result_transformer_=Result.value)
        if len(r) == 0 or r[0] is None:
            raise ValueError("Modular procedure not found.")
        return PublishModularProcedureModel(tag=tag, version=r[0], content_hash=content_hash)

    def link(self, tag: str, submission_tag: str, user_tag: str) -> bool:
        "Assigns a submission to the procedure, appended at the end of the submission's procedure order."
        if not self.exists(tag=tag):
            raise ValueError("Modular procedure not found.")
        already_linked = self._driver.execute_query(
            "WITH EXISTS {(s:Submission {tag : $submission_tag})-[:IN_PROCEDURE]->(m:ModularProcedure {tag : $tag})} as exists RETURN exists",
            routing_="r", tag=tag, submission_tag=submission_tag, result_transformer_=Result.value)
        if len(already_linked) > 0 and already_linked[0]:
            raise ValueError("Submission is already linked to this modular procedure.")
        query = (
            "MATCH (m:ModularProcedure {tag : $tag}) "
            "MATCH (s:Submission {tag : $submission_tag}) "
            "OPTIONAL MATCH (s)-[existing:IN_PROCEDURE]->() "
            "WITH m, s, count(existing) as n_links "
            "CREATE (s)-[:IN_PROCEDURE {position : n_links, created_at : $created_at, done : false, done_at : null, done_by : null}]->(m) "
            "RETURN true as success"
        )
        r = self._driver.execute_query(query, routing_="w", tag=tag, submission_tag=submission_tag,
                                       created_at=time.time(), result_transformer_=Result.value)
        return len(r) > 0 and r[0] is not None

    def unlink(self, tag: str, submission_tag: str) -> bool:
        "Removes the submission from the procedure."
        query = (
            "MATCH (s:Submission {tag : $submission_tag})-[r:IN_PROCEDURE]->(m:ModularProcedure {tag : $tag}) "
            "DELETE r "
            "RETURN count(r) as n_deleted"
        )
        r = self._driver.execute_query(query, routing_="w", tag=tag, submission_tag=submission_tag,
                                       result_transformer_=Result.value)
        if len(r) == 0 or r[0] == 0:
            raise ValueError("Submission is not linked to this modular procedure.")
        return True

    def mark_done(self, tag: str, submission_tag: str, user_tag: str) -> bool:
        "Marks the submission as done in the given procedure."
        query = (
            "MATCH (s:Submission {tag : $submission_tag})-[r:IN_PROCEDURE]->(m:ModularProcedure {tag : $tag}) "
            "SET r.done = true, r.done_at = $done_at, r.done_by = $user_tag "
            "RETURN r.done as done"
        )
        r = self._driver.execute_query(query, routing_="w", tag=tag, submission_tag=submission_tag,
                                       done_at=time.time(), user_tag=user_tag, result_transformer_=Result.value)
        if len(r) == 0 or r[0] is None:
            raise ValueError("Submission is not linked to this modular procedure.")
        return True

    def reopen(self, tag: str, submission_tag: str) -> bool:
        "Reverts the done flag of the submission in the given procedure."
        query = (
            "MATCH (s:Submission {tag : $submission_tag})-[r:IN_PROCEDURE]->(m:ModularProcedure {tag : $tag}) "
            "SET r.done = false, r.done_at = null, r.done_by = null "
            "RETURN r.done as done"
        )
        r = self._driver.execute_query(query, routing_="w", tag=tag, submission_tag=submission_tag,
                                       result_transformer_=Result.value)
        if len(r) == 0 or r[0] is None:
            raise ValueError("Submission is not linked to this modular procedure.")
        return True

    def get_submissions(self, tag: str) -> List[ModularProcedureSubmissionModel]:
        "Returns the submissions linked to the given procedure with their link information."
        query = (
            "MATCH (s:Submission)-[r:IN_PROCEDURE]->(m:ModularProcedure {tag : $tag}) "
            "RETURN {procedure_tag: $tag, submission_tag: s.tag, position: r.position, "
            "created_at: r.created_at, done: r.done, done_at: r.done_at, done_by: r.done_by} as link "
            "ORDER BY r.created_at ASC"
        )
        r = self._driver.execute_query(query, routing_="r", tag=tag, result_transformer_=Result.data)
        if len(r) == 0 and not self.exists(tag=tag):
            raise KeyError("Modular procedure not found.")
        return [ModularProcedureSubmissionModel(**row["link"]) for row in r]

    def get_submission_procedures(self, submission_tag: str) -> List[ModularProcedureSubmissionModel]:
        "Returns the procedures the given submission is linked to, ordered by link position."
        query = (
            "MATCH (s:Submission {tag : $submission_tag})-[r:IN_PROCEDURE]->(m:ModularProcedure) "
            "RETURN {procedure_tag: m.tag, submission_tag: $submission_tag, position: r.position, "
            "created_at: r.created_at, done: r.done, done_at: r.done_at, done_by: r.done_by} as link "
            "ORDER BY r.position ASC"
        )
        r = self._driver.execute_query(query, routing_="r", submission_tag=submission_tag, result_transformer_=Result.data)
        return [ModularProcedureSubmissionModel(**row["link"]) for row in r]

    def get_condition_applications(self, tag: str) -> List[str]:
        "Returns the condition application tags of the given procedure."
        query = (
            "MATCH (m:ModularProcedure {tag : $tag})-[:HAS_CONDITION_APPLICATION]->(c:ConditionApplication) "
            "RETURN c.tag as tag"
        )
        r = self._driver.execute_query(query, routing_="r", tag=tag, result_transformer_=Result.value)
        return r

    def get_protocols(self, tag: str) -> List[str]:
        "Returns the protocol tags of the given procedure."
        query = (
            "MATCH (m:ModularProcedure {tag : $tag})-[:HAS_PROTOCOL]->(p:Protocol) "
            "RETURN p.tag as tag"
        )
        r = self._driver.execute_query(query, routing_="r", tag=tag, result_transformer_=Result.value)
        return r

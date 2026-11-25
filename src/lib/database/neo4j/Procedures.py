import hashlib
import json
import time

from neo4j import Driver, Result
from typing import Dict, List, Optional

from lib.cache.scope_cache import invalidate_all_cached_scopes
from lib.database.abstract.Procedures import ModularProceduresABC
from lib.database.neo4j.Plates import STORAGE_GROUP_TAG
from services.encryption import create_hierarchical_hash
from config.models.procedures import (
    ModularProcedureBaseModel,
    ModularProcedureSubmissionModel,
    PublishModularProcedureModel,
)

EXECUTION_STATE_TAGS = ["DRAFT", "RUNNING", "SUCCEEDED", "FAILED", "ABORTED"]



class Neo4JModularProcedures(ModularProceduresABC):

    def __init__(self, driver: Driver, condition_applications=None) -> None:
        self._driver = driver
        self._condition_applications = condition_applications

    def _resolve_condition_application_tags(self, condition_application_tags, condition_application_trees) -> List[str]:
        """Combines reused condition application tags with newly defined attribute/trait trees:
        each tree is inserted via the condition applications database (idempotent, hash-tagged)
        and the resulting tags are merged with the reused ones."""
        tags = list(condition_application_tags or [])
        for tree in (condition_application_trees or []):
            ca_tag = self._condition_applications.insert(tree)
            if ca_tag not in tags:
                tags.append(ca_tag)
        return tags

    def _compute_content_hash(self, title: str, description: str,
                               condition_application_tags: List[str],
                               protocol_tags: List[str],
                               plate_constraints: dict = None,
                               input_attribute_tags: List[str] = None,
                               output_attribute_tags: List[str] = None,
                               success_submission_state: str = None,
                               required_submission_state: str = None,
                               pubmed_ids: List[str] = None,
                               min_output_wells_per_sample: int = 1,
                               max_output_wells_per_sample: int = None) -> str:
        "Computes the SHA-256 hash over the canonical serialization of the procedure content."
        content = {
            "title": title,
            "description": description,
            "condition_application_tags": sorted(condition_application_tags or []),
            "protocol_tags": sorted(protocol_tags or []),
            "plate_constraints": plate_constraints or {},
            "input_attribute_tags": sorted(input_attribute_tags or []),
            "output_attribute_tags": sorted(output_attribute_tags or []),
            "success_submission_state": success_submission_state,
            "required_submission_state": required_submission_state,
            "pubmed_ids": sorted(pubmed_ids or []),
            "min_output_wells_per_sample": min_output_wells_per_sample,
            "max_output_wells_per_sample": max_output_wells_per_sample,
        }
        return hashlib.sha256(json.dumps(content, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()

    def _validate_success_submission_state(self, success_submission_state) -> None:
        """Validates that the optional success submission state is the name of a submission state."""
        from config.enums.states import SubmissionStatesEnums
        if success_submission_state is None:
            return
        if success_submission_state not in [state.name for state in SubmissionStatesEnums]:
            raise ValueError(f"Unknown submission state: {success_submission_state}")

    def _validate_attributes(self, attribute_tags: List[str], relationship: str, tag: str) -> None:
        """Validates that the given attributes exist and links them to the procedure with the given relationship."""
        for attribute_tag in attribute_tags or []:
            attribute_exists = self._driver.execute_query(
                "WITH EXISTS {(a:Attribute {tag : $attribute_tag})} as exists RETURN exists",
                routing_="r", attribute_tag=attribute_tag, result_transformer_=Result.value)
            if len(attribute_exists) == 0 or not attribute_exists[0]:
                raise ValueError(f"Attribute not found: {attribute_tag}")
            self._driver.execute_query(
                f"MATCH (m:ModularProcedure {{tag : $tag}}) MATCH (a:Attribute {{tag : $attribute_tag}}) "
                f"MERGE (m)-[:{relationship}]->(a) ",
                routing_="w", tag=tag, attribute_tag=attribute_tag)

    def _link_procedure_attributes(self, tag: str, input_attribute_tags: List[str],
                                    output_attribute_tags: List[str]) -> None:
        """Replaces the attribute declarations of the procedure."""
        self._driver.execute_query(
            "MATCH (m:ModularProcedure {tag : $tag})-[r:ACCEPTS_INPUT_ATTRIBUTE|EXPECTS_OUTPUT_ATTRIBUTE]->() DELETE r",
            routing_="w", tag=tag)
        self._validate_attributes(input_attribute_tags, "ACCEPTS_INPUT_ATTRIBUTE", tag)
        self._validate_attributes(output_attribute_tags, "EXPECTS_OUTPUT_ATTRIBUTE", tag)

    def exists(self, tag: str) -> bool:
        query = "WITH EXISTS {(m:ModularProcedure {tag : $tag})} as exists RETURN exists"
        r = self._driver.execute_query(query, routing_="r", tag=tag, result_transformer_=Result.value)
        return r[0] if len(r) > 0 else False

    def _validate_sample_multiplicity(self, min_output_wells_per_sample, max_output_wells_per_sample) -> None:
        "Validates the per-sample output well bounds of a procedure."
        if min_output_wells_per_sample is None:
            min_output_wells_per_sample = 1
        if not isinstance(min_output_wells_per_sample, int) or min_output_wells_per_sample < 1:
            raise ValueError("min_output_wells_per_sample must be an integer >= 1.")
        if max_output_wells_per_sample is not None:
            if not isinstance(max_output_wells_per_sample, int) or max_output_wells_per_sample < min_output_wells_per_sample:
                raise ValueError("max_output_wells_per_sample must be an integer >= min_output_wells_per_sample or None.")

    def insert(self, title: str, description: str, user_tag: str,
               condition_application_tags: List[str] = None,
               condition_application_trees: List = None,
               protocol_tags: List[str] = None,
               plate_constraints: dict = None,
               input_attribute_tags: List[str] = None,
               output_attribute_tags: List[str] = None,
               success_submission_state: str = None,
               required_submission_state: str = None,
               pubmed_ids: List[str] = None,
               min_output_wells_per_sample: int = 1,
               max_output_wells_per_sample: int = None) -> str:
        """Inserts a new draft modular procedure. The tag is generated based on the title,
        description, condition applications and version. Condition applications can be reused
        by tag or newly defined as attribute/trait trees (resolved to tags on insert)."""
        condition_application_tags = self._resolve_condition_application_tags(condition_application_tags, condition_application_trees)
        protocol_tags = protocol_tags or []
        plate_constraints = plate_constraints or {}
        self._validate_success_submission_state(success_submission_state)
        self._validate_success_submission_state(required_submission_state)
        self._validate_plate_constraint_texts(plate_constraints)
        self._validate_sample_multiplicity(min_output_wells_per_sample, max_output_wells_per_sample)
        tag = create_hierarchical_hash([title, description, sorted(condition_application_tags), "1"])
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
            "lineage_tag": tag,
            "user_tag": user_tag,
            "input_plate_format": plate_constraints.get("input_plate_format"),
            "input_plate_type": plate_constraints.get("input_plate_type"),
            "output_plate_format": plate_constraints.get("output_plate_format"),
            "output_plate_type": plate_constraints.get("output_plate_type"),
            "success_submission_state": success_submission_state,
            "required_submission_state": required_submission_state,
            "pubmed_ids": list(pubmed_ids or []),
            "min_output_wells_per_sample": min_output_wells_per_sample if min_output_wells_per_sample is not None else 1,
            "max_output_wells_per_sample": max_output_wells_per_sample,
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

        self._link_procedure_attributes(tag=tag, input_attribute_tags=input_attribute_tags,
                                         output_attribute_tags=output_attribute_tags)

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
            "OPTIONAL MATCH (m)-[:ACCEPTS_INPUT_ATTRIBUTE]->(ia:Attribute) "
            "OPTIONAL MATCH (m)-[:EXPECTS_OUTPUT_ATTRIBUTE]->(oa:Attribute) "
            "WITH m, collect(DISTINCT c.tag) as ca_tags, collect(DISTINCT p.tag) as protocol_tags, "
            "collect(DISTINCT ia.tag) as input_attribute_tags, collect(DISTINCT oa.tag) as output_attribute_tags "
            "RETURN {tag: m.tag, title: m.title, description: m.description, status: m.status, "
            "version: m.version, lineage_tag: m.lineage_tag, content_hash: m.content_hash, user_tag: m.user_tag, "
            "created_at: m.created_at, published_at: m.published_at, "
            "condition_application_tags: [tag IN ca_tags WHERE tag IS NOT NULL], "
            "protocol_tags: [tag IN protocol_tags WHERE tag IS NOT NULL], "
            "input_plate_format: m.input_plate_format, input_plate_type: m.input_plate_type, "
            "output_plate_format: m.output_plate_format, output_plate_type: m.output_plate_type, "
            "input_attribute_tags: [tag IN input_attribute_tags WHERE tag IS NOT NULL], "
            "output_attribute_tags: [tag IN output_attribute_tags WHERE tag IS NOT NULL], "
            "success_submission_state: m.success_submission_state, "
            "required_submission_state: m.required_submission_state, "
            "pubmed_ids: coalesce(m.pubmed_ids, []), "
            "min_output_wells_per_sample: coalesce(m.min_output_wells_per_sample, 1), "
            "max_output_wells_per_sample: m.max_output_wells_per_sample} as procedure"
        )
        r = self._driver.execute_query(query, routing_="r", tag=tag, result_transformer_=Result.data)
        if len(r) == 0:
            raise KeyError("Modular procedure not found.")
        return ModularProcedureBaseModel(**r[0]["procedure"])

    def find(self, search_string: str = None, status: str = None, limit: int = None, latest_only: bool = False) -> List[str]:
        """Returns the tags of modular procedures, sorted by creation date, most recent last.
        If latest_only is True, only the highest-version procedure of each lineage is returned."""
        query = "MATCH (m:ModularProcedure) "
        params = {}
        if search_string is not None:
            query += "WHERE m.title CONTAINS $search_string "
            params["search_string"] = search_string
        if status is not None:
            query += ("AND " if "WHERE" in query else "WHERE ") + "m.status = $status "
            params["status"] = status
        if latest_only:
            query += ("AND " if "WHERE" in query else "WHERE ") + "NOT EXISTS { "
            query += "MATCH (m2:ModularProcedure {lineage_tag : m.lineage_tag}) "
            if status is not None:
                query += "WHERE m2.status = $status AND m2.version > m.version "
            else:
                query += "WHERE m2.version > m.version "
            query += "} "
        query += "RETURN m.tag as tag ORDER BY m.created_at ASC"
        if limit is not None:
            query += " LIMIT $limit"
            params["limit"] = limit
        r = self._driver.execute_query(query, routing_="r", parameters_=params, result_transformer_=Result.value)
        return r

    def create_version(self, tag: str, user_tag: str) -> "ModularProcedureBaseModel":
        """Creates a new draft version of the given published modular procedure, copying its content.
        Submissions stay linked to the version they were assigned to."""
        parent = self.get(tag=tag)
        if parent.status != "PUBLISHED":
            raise ValueError("New versions can only be created from published modular procedures.")
        max_version = self._driver.execute_query(
            "MATCH (m:ModularProcedure {lineage_tag : $lineage_tag}) "
            "RETURN max(m.version) as max_version",
            routing_="r", lineage_tag=parent.lineage_tag, result_transformer_=Result.value)
        new_version = (max_version[0] if len(max_version) > 0 and max_version[0] is not None else parent.version) + 1
        new_tag = create_hierarchical_hash([parent.title, parent.description,
                                            sorted(parent.condition_application_tags), str(new_version)])
        if self.exists(tag=new_tag):
            raise ValueError("Tag is already in the database.")

        query = (
            "MATCH (u:User {tag : $user_tag}) "
            "MERGE (m:ModularProcedure {tag : $tag}) "
            "SET m.created_at = timestamp(), m += $props "
            "MERGE (u)-[:CREATED]->(m) "
            "WITH m "
            "MATCH (parent:ModularProcedure {tag : $parent_tag}) "
            "MERGE (m)-[:PREVIOUS_VERSION]->(parent) "
            "RETURN m.tag as tag"
        )
        props = {
            "title": parent.title,
            "description": parent.description,
            "status": "DRAFT",
            "version": new_version,
            "lineage_tag": parent.lineage_tag,
            "user_tag": user_tag,
            "input_plate_format": parent.input_plate_format,
            "input_plate_type": parent.input_plate_type,
            "output_plate_format": parent.output_plate_format,
            "output_plate_type": parent.output_plate_type,
            "success_submission_state": parent.success_submission_state,
            "required_submission_state": parent.required_submission_state,
            "pubmed_ids": list(parent.pubmed_ids or []),
            "min_output_wells_per_sample": parent.min_output_wells_per_sample if parent.min_output_wells_per_sample is not None else 1,
            "max_output_wells_per_sample": parent.max_output_wells_per_sample,
        }
        r = self._driver.execute_query(query, routing_="w", tag=new_tag, user_tag=user_tag,
                                       parent_tag=tag, props=props, result_transformer_=Result.value)
        if len(r) == 0 or r[0] is None:
            raise ValueError("Modular procedure version could not be created.")

        self._link_procedure_attributes(tag=new_tag, input_attribute_tags=parent.input_attribute_tags,
                                         output_attribute_tags=parent.output_attribute_tags)

        for ca_tag in parent.condition_application_tags:
            self._driver.execute_query(
                "MATCH (m:ModularProcedure {tag : $tag}) MATCH (c:ConditionApplication {tag : $ca_tag}) "
                "MERGE (m)-[:HAS_CONDITION_APPLICATION]->(c)",
                routing_="w", tag=new_tag, ca_tag=ca_tag)
        for protocol_tag in parent.protocol_tags:
            self._driver.execute_query(
                "MATCH (m:ModularProcedure {tag : $tag}) MATCH (p:Protocol {tag : $protocol_tag}) "
                "MERGE (m)-[:HAS_PROTOCOL]->(p)",
                routing_="w", tag=new_tag, protocol_tag=protocol_tag)

        return self.get(tag=new_tag)

    def get_versions(self, tag: str) -> List[str]:
        "Returns the tags of all versions in the lineage of the given procedure, oldest first."
        procedure = self.get(tag=tag)
        return self._driver.execute_query(
            "MATCH (m:ModularProcedure {lineage_tag : $lineage_tag}) "
            "RETURN m.tag as tag ORDER BY m.version ASC",
            routing_="r", lineage_tag=procedure.lineage_tag, result_transformer_=Result.value)

    def update(self, tag: str, title: str, description: str, user_tag: str,
               condition_application_tags: List[str] = None,
               condition_application_trees: List = None,
               protocol_tags: List[str] = None,
               plate_constraints: dict = None,
               input_attribute_tags: List[str] = None,
               output_attribute_tags: List[str] = None,
               success_submission_state: str = None,
               required_submission_state: str = None) -> bool:
        "Updates a draft modular procedure. Published procedures are immutable."
        if not self.exists(tag=tag):
            raise ValueError("Modular procedure not found.")
        if self.get(tag=tag).status == "PUBLISHED":
            raise ValueError("Published modular procedures are immutable.")
        condition_application_tags = self._resolve_condition_application_tags(condition_application_tags, condition_application_trees)
        protocol_tags = protocol_tags or []
        plate_constraints = plate_constraints or {}
        self._validate_success_submission_state(success_submission_state)
        self._validate_success_submission_state(required_submission_state)
        self._validate_plate_constraint_texts(plate_constraints)

        query = (
            "MATCH (m:ModularProcedure {tag : $tag}) "
            "OPTIONAL MATCH (m)-[r:HAS_CONDITION_APPLICATION]->() DELETE r "
            "WITH DISTINCT m "
            "OPTIONAL MATCH (m)-[r2:HAS_PROTOCOL]->() DELETE r2 "
            "WITH DISTINCT m "
            "MATCH (u:User {tag : $user_tag}) "
            "SET m.title = $title, m.description = $description, m.modified_at = timestamp(), "
            "m.input_plate_format = $input_plate_format, m.input_plate_type = $input_plate_type, "
            "m.output_plate_format = $output_plate_format, m.output_plate_type = $output_plate_type, "
            "m.success_submission_state = $success_submission_state, "
            "m.required_submission_state = $required_submission_state, "
            "m.pubmed_ids = $pubmed_ids, "
            "m.min_output_wells_per_sample = $min_output_wells_per_sample, "
            "m.max_output_wells_per_sample = $max_output_wells_per_sample "
            "MERGE (u)-[:UPDATED]->(m) "
            "RETURN m.tag as tag"
        )
        plate_props = {
            "input_plate_format": plate_constraints.get("input_plate_format"),
            "input_plate_type": plate_constraints.get("input_plate_type"),
            "output_plate_format": plate_constraints.get("output_plate_format"),
            "output_plate_type": plate_constraints.get("output_plate_type"),
            "success_submission_state": success_submission_state,
            "required_submission_state": required_submission_state,
            "pubmed_ids": list(pubmed_ids or []),
            "min_output_wells_per_sample": min_output_wells_per_sample if min_output_wells_per_sample is not None else 1,
            "max_output_wells_per_sample": max_output_wells_per_sample,
        }
        r = self._driver.execute_query(query, routing_="w", tag=tag, title=title, description=description,
                                       user_tag=user_tag, **plate_props, result_transformer_=Result.value)
        if len(r) == 0 or r[0] is None:
            return False

        for ca_tag in condition_application_tags:
            self._driver.execute_query(
                "MATCH (m:ModularProcedure {tag : $tag}) MATCH (c:ConditionApplication {tag : $ca_tag}) "
                "MERGE (m)-[:HAS_CONDITION_APPLICATION]->(c)",
                routing_="w", tag=tag, ca_tag=ca_tag)

        self._link_procedure_attributes(tag=tag, input_attribute_tags=input_attribute_tags,
                                         output_attribute_tags=output_attribute_tags)

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
        content_hash = self._compute_content_hash(
            title=procedure.title, description=procedure.description,
            condition_application_tags=procedure.condition_application_tags,
            protocol_tags=procedure.protocol_tags,
            plate_constraints={"input_plate_format": procedure.input_plate_format,
                               "input_plate_type": procedure.input_plate_type,
                               "output_plate_format": procedure.output_plate_format,
                               "output_plate_type": procedure.output_plate_type},
            input_attribute_tags=procedure.input_attribute_tags,
            output_attribute_tags=procedure.output_attribute_tags,
            success_submission_state=procedure.success_submission_state,
            required_submission_state=procedure.required_submission_state,
            pubmed_ids=procedure.pubmed_ids,
            min_output_wells_per_sample=procedure.min_output_wells_per_sample,
            max_output_wells_per_sample=procedure.max_output_wells_per_sample)
        query = (
            "MATCH (m:ModularProcedure {tag : $tag}) "
            "MATCH (u:User {tag : $user_tag}) "
            "SET m.status = 'PUBLISHED', m.content_hash = $content_hash, "
            "m.published_at = timestamp() "
            "MERGE (u)-[:PUBLISHED]->(m) "
            "RETURN m.version as version"
        )
        r = self._driver.execute_query(query, routing_="w", tag=tag, content_hash=content_hash,
                                       user_tag=user_tag, result_transformer_=Result.value)
        if len(r) == 0 or r[0] is None:
            raise ValueError("Modular procedure not found.")
        return PublishModularProcedureModel(tag=tag, version=r[0], content_hash=content_hash)

    def retire(self, tag: str, user_tag: str) -> "ModularProcedureBaseModel":
        """Retires a published modular procedure: the content (and its SHA-256 hash) stay exactly
        as they are and procedures are never deleted — the procedure keeps running the module
        history of its submissions and its executions stay reproducible — but the procedure is
        marked retired: greyed out in the UI and no longer assignable or executable. Existing
        links are untouched (their submissions can still be marked done)."""
        procedure = self.get(tag=tag)
        if procedure.status == "RETIRED":
            raise ValueError("This modular procedure is already retired.")
        if procedure.status != "PUBLISHED":
            raise ValueError("Only published modular procedures can be retired.")
        self._driver.execute_query(
            "MATCH (m:ModularProcedure {tag : $tag}) MATCH (u:User {tag : $user_tag}) "
            "SET m.status = 'RETIRED', m.retired_at = timestamp() "
            "MERGE (u)-[:RETIRED]->(m) ",
            routing_="w", tag=tag, user_tag=user_tag)
        return self.get(tag=tag)

    def link(self, tag: str, submission_tag: str, user_tag: str) -> bool:
        """Assigns a submission to the procedure, appended at the end of the submission's procedure
        order. Retired procedures can no longer be assigned; already linked submissions keep their
        module history and can still be marked done."""
        if not self.exists(tag=tag):
            raise ValueError("Modular procedure not found.")
        if self.get(tag=tag).status == "RETIRED":
            raise ValueError("This modular procedure is retired and can no longer be assigned to submissions.")
        already_linked = self._driver.execute_query(
            "WITH EXISTS {(s:Submission {tag : $submission_tag})-[:IN_PROCEDURE]->(m:ModularProcedure {tag : $tag})} as exists RETURN exists",
            routing_="r", tag=tag, submission_tag=submission_tag, result_transformer_=Result.value)
        if len(already_linked) > 0 and already_linked[0]:
            raise ValueError("Submission is already linked to this modular procedure.")
        open_elsewhere = self._driver.execute_query(
            "MATCH (s:Submission {tag : $submission_tag})-[r:IN_PROCEDURE]->(m:ModularProcedure) "
            "WHERE m.tag <> $tag AND r.done = false "
            "RETURN collect(m.tag) as open_procedures",
            routing_="r", tag=tag, submission_tag=submission_tag, result_transformer_=Result.value)
        if len(open_elsewhere) > 0 and len(open_elsewhere[0]) > 0:
            raise ValueError(f"Submission is not done in another modular procedure yet: {', '.join(open_elsewhere[0])}. "
                             "A submission can only be linked to one modular procedure at a time.")
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

    @staticmethod
    def _parse_position(position: str):
        "Parses a well position like 'A1' into (row_index, column_index)."
        import re
        match = re.match(r"^([A-Z]+)([0-9]+)$", str(position).upper().strip())
        if match is None:
            raise ValueError(f"Invalid well position: {position}")
        row = 0
        for character in match.group(1):
            row = row * 26 + (ord(character) - ord("A") + 1)
        return row - 1, int(match.group(2)) - 1

    def _validate_plate_constraint_texts(self, plate_constraints: dict) -> None:
        """Validates that the format and type texts of the plate constraints exist in the storage
        attribute group (which defines the plates): a format text must be the text of a trait whose
        value defines the container format (e.g. '8x12' -> the 96 well plate), a type text must be
        the text of any other selectable trait of the group. Typos are rejected when the procedure
        is defined instead of silently blocking every execution."""
        trait_rows = self._driver.execute_query(
            "MATCH (a:Attribute)-[:PART_OF]->(:AttributeGroup {tag : $group_tag}) "
            "MATCH (a)-[:HAS_TRAIT]->(t:Trait) "
            "RETURN t.text as text, t.value as value",
            routing_="r", group_tag=STORAGE_GROUP_TAG, result_transformer_=Result.data)
        import re
        known_formats, known_types = [], []
        for row in trait_rows:
            if re.match(r"^[0-9]+x[0-9]+$", str(row["value"] or "")):
                known_formats.append(row["text"])
            else:
                known_types.append(row["text"])
        for side in ("input", "output"):
            required_format = (plate_constraints or {}).get(f"{side}_plate_format")
            required_type = (plate_constraints or {}).get(f"{side}_plate_type")
            if required_format is not None and required_format not in known_formats:
                raise ValueError(f"Unknown plate format: {required_format}. Known formats: {', '.join(known_formats)}.")
            if required_type is not None and required_type not in known_types:
                raise ValueError(f"Unknown plate type: {required_type}. Known types: {', '.join(known_types)}.")

    def _validate_plate_constraints(self, procedure, plate_tag: str, side: str) -> None:
        """Validates that the given plate matches the plate layout constraints the procedure defines
        for the given side (input or output): the format (the text of the plate's selected container
        format trait, e.g. '8x12') and the type (any other trait selected for the plate from the
        storage attribute group). Unconstrained sides always pass."""
        required_format = getattr(procedure, f"{side}_plate_format")
        required_type = getattr(procedure, f"{side}_plate_type")
        if required_format is None and required_type is None:
            return
        plate_props = self._driver.execute_query(
            "MATCH (p:Plate {tag : $plate_tag}) "
            "OPTIONAL MATCH (p)-[:HAS_APPLICATION]->(:ConditionApplication)-[:INSTANCE_OF]->(t:Trait) "
            "WITH p, collect(DISTINCT t.text) as trait_texts "
            "RETURN {format: p.format, trait_texts: trait_texts} as plate",
            routing_="r", plate_tag=plate_tag, result_transformer_=Result.data)
        if len(plate_props) == 0:
            raise ValueError(f"Plate not found: {plate_tag}")
        plate = plate_props[0]["plate"] or {}
        if required_format is not None and plate.get("format") != required_format:
            raise ValueError(f"The {side} plate of this procedure must have the format {required_format}, "
                             f"but the plate has {plate.get('format')}.")
        if required_type is not None and required_type not in (plate.get("trait_texts") or []):
            raise ValueError(f"The {side} plate of this procedure must be of type {required_type} "
                             f"(a matching selected trait of the plate).")

    def _set_execution_state(self, execution_tag: str, state: str, user_tag: str) -> None:
        """Appends a state to the execution's state history: creates an IN_STATE relationship to
        the ProcessingState node with created_at and user_tag, and keeps the status property
        (the current state) in sync."""
        if state not in EXECUTION_STATE_TAGS:
            raise ValueError(f"Unknown procedure execution state: {state}")
        self._driver.execute_query(
            "MERGE (ps:ProcessingState {tag : $state}) "
            "WITH ps MATCH (e:ModularProcedureExecution {tag : $execution_tag}) "
            "CREATE (e)-[r:IN_STATE]->(ps) "
            "SET r.created_at = $created_at, r.user_tag = $user_tag, e.status = $state ",
            routing_="w", state=state, execution_tag=execution_tag,
            created_at=time.time(), user_tag=user_tag)

    def get_execution_states(self, execution_tag: str) -> List:
        """Returns the state history of a procedure execution, newest state first:"""
        from config.models.procedures import ExecutionStateModel
        execution_exists = self._driver.execute_query(
            "WITH EXISTS {(e:ModularProcedureExecution {tag : $execution_tag})} as exists RETURN exists",
            routing_="r", execution_tag=execution_tag, result_transformer_=Result.value)
        if len(execution_exists) == 0 or not execution_exists[0]:
            raise KeyError("Procedure execution not found.")
        rows = self._driver.execute_query(
            "MATCH (e:ModularProcedureExecution {tag : $execution_tag})-[r:IN_STATE]->(ps:ProcessingState) "
            "RETURN {state: ps.tag, created_at: r.created_at, user_tag: r.user_tag} as state "
            "ORDER BY r.created_at DESC",
            routing_="r", execution_tag=execution_tag, result_transformer_=Result.data)
        return [ExecutionStateModel(**row["state"]) for row in rows]

    def get_current_execution_state(self, execution) -> str:
        """Returns the current state of the execution: the newest IN_STATE state, falling back
        to the status property for executions created before the state history existed."""
        current = self._driver.execute_query(
            "MATCH (e:ModularProcedureExecution {tag : $execution_tag})-[r:IN_STATE]->(ps:ProcessingState) "
            "RETURN ps.tag as state ORDER BY r.created_at DESC LIMIT 1",
            routing_="r", execution_tag=execution.tag, result_transformer_=Result.value)
        return current[0] if len(current) > 0 and current[0] is not None else (execution.status or "RUNNING")

    def get_submission_sample_locations(self, submission_tag: str) -> List:
        """Returns the current plate locations of the samples of a submission: for every sample
        the wells of its most recent procedure execution (input and output side, with the plate
        tags), newest execution first. Samples that were never placed show no entry.
        Raises a KeyError if the submission does not exist."""
        from config.models.procedures import SampleLocationModel
        submission_exists = self._driver.execute_query(
            "WITH EXISTS {(s:Submission {tag : $submission_tag})} as exists RETURN exists",
            routing_="r", submission_tag=submission_tag, result_transformer_=Result.value)
        if len(submission_exists) == 0 or not submission_exists[0]:
            raise KeyError("Submission not found.")
        rows = self._driver.execute_query(
            "MATCH (sub:Submission {tag : $submission_tag})-[:HAS_SAMPLE]->(sample:Sample)-[:IN_WELL]->(w:ExecutionWell) "
            "MATCH (e:ModularProcedureExecution)-[:HAS_WELL]->(w) "
            "RETURN {sample_tag: sample.tag, procedure_tag: e.procedure_tag, execution_tag: e.tag, "
            "status: coalesce(e.status, 'RUNNING'), created_at: e.created_at, "
            "position: w.position, side: w.side, "
            "plate_tag: coalesce(w.plate_tag, CASE w.side WHEN 'INPUT' THEN e.input_plate_tag "
            "ELSE e.output_plate_tag END)} as location ",
            routing_="r", submission_tag=submission_tag, result_transformer_=Result.data)
        placed = {}
        for row in rows:
            location = row["location"]
            placed.setdefault(location["sample_tag"], []).append(location)
        locations = []
        for sample_tag, entries in placed.items():
            latest_created_at = max(entry["created_at"] or 0 for entry in entries)
            latest = [entry for entry in entries if (entry["created_at"] or 0) == latest_created_at]
            head = latest[0]
            locations.append(SampleLocationModel(
                sample_tag=sample_tag, procedure_tag=head["procedure_tag"],
                execution_tag=head["execution_tag"], execution_status=head["status"],
                created_at=head["created_at"],
                wells=[{"plate_tag": entry["plate_tag"], "position": entry["position"], "side": entry["side"]}
                       for entry in latest]))
        return sorted(locations, key=lambda location: location.sample_tag)

    def get_sample_submission_map(self, sample_tags: List[str]) -> "dict":
        """Returns a map of the given sample tags to the tags of the submissions owning them."""
        if not sample_tags:
            return {}
        rows = self._driver.execute_query(
            "MATCH (s:Submission)-[:HAS_SAMPLE]->(sample:Sample) "
            "WHERE sample.tag IN $sample_tags "
            "RETURN sample.tag as sample_tag, collect(DISTINCT s.tag) as submission_tags",
            routing_="r", sample_tags=list(sample_tags), result_transformer_=Result.data)
        return {row["sample_tag"]: row["submission_tags"] for row in rows}

    def find_execution_tags_by_submissions(self, submission_tags: List[str]) -> List[str]:
        """Returns the tags of the procedure executions that placed samples of the given submissions."""
        if not submission_tags:
            return []
        return self._driver.execute_query(
            "MATCH (s:Submission)-[:HAS_SAMPLE]->(:Sample)-[:IN_WELL]->(w:ExecutionWell) "
            "WHERE s.tag IN $submission_tags "
            "MATCH (e:ModularProcedureExecution)-[:HAS_WELL]->(w) "
            "RETURN DISTINCT e.tag as tag ORDER BY tag",
            routing_="r", submission_tags=list(submission_tags), result_transformer_=Result.value)

    @staticmethod
    def _group_by_plate(well_keys) -> dict:
        """Groups (plate_tag, position) well keys into a map of plate tag to its positions."""
        grouped = {}
        for plate_tag, position in well_keys:
            grouped.setdefault(plate_tag, set()).add(position)
        return grouped

    @staticmethod
    def _design_plate_tags(execution, side: str) -> List[str]:
        """The effective plate list of one side (input / output) of an execution design: the
        primary plate first, followed by the additional plates (multi-plate support for large
        sample numbers), duplicates removed while preserving the order."""
        from config.models.procedures import split_well_ref  # noqa: F401 (documented well ref convention)
        primary = getattr(execution, f"{side}_plate_tag", None)
        additional = list(getattr(execution, f"additional_{side}_plate_tags", None) or [])
        ordered, seen = [], set()
        for plate_tag in ([primary] if primary else []) + additional:
            if plate_tag not in seen:
                seen.add(plate_tag)
                ordered.append(plate_tag)
        return ordered

    @staticmethod
    def _well_plate(well, primary_plate_tag: str) -> str:
        """The plate a design well is on: the well's own plate tag or the primary plate."""
        return getattr(well, "plate_tag", None) or primary_plate_tag

    def _validate_execution_design(self, procedure, execution, user_tag) -> dict:
        """Full design validation of an execution: the plates must exist, the responsible user must
        be a curator, the plates must match the procedure's layout constraints, well positions
        must be unique and every transfer target defined, metrics must reference declared traits
        and the transfer map must respect the declared sample numbers (mirroring / N-fold
        duplication). Returns the derived storage data. The occupancy of the output wells is
        checked separately (only when an execution actually starts running)."""
        from config.models.procedures import split_well_ref
        input_plates = self._design_plate_tags(execution, "input")
        output_plates = self._design_plate_tags(execution, "output")
        # a draft can be saved at any stage: an empty design (no wells, no metrics) may omit one or
        # both plates - the design is completed by a later save and fully validated when starting
        empty_design = (len(execution.input_wells) == 0 and len(execution.output_wells) == 0
                        and len(execution.output_well_metrics or []) == 0
                        and len(getattr(execution, "input_well_metrics", None) or []) == 0)
        for side, plate_tags in (("input", input_plates), ("output", output_plates)):
            if len(plate_tags) == 0:
                if empty_design:
                    continue
                raise ValueError("Input and output plates must be defined.")
            for plate_tag in plate_tags:
                plate_exists = self._driver.execute_query(
                    "WITH EXISTS {(p:Plate {tag : $plate_tag})} as exists RETURN exists",
                    routing_="r", plate_tag=plate_tag, result_transformer_=Result.value)
                if len(plate_exists) == 0 or not plate_exists[0]:
                    raise ValueError(f"Plate not found: {plate_tag}")

        responsible_user_tag = execution.responsible_user_tag or user_tag
        responsible_user = self._driver.execute_query(
            "MATCH (u:User {tag : $user_tag}) RETURN u.role as role",
            routing_="r", user_tag=responsible_user_tag, result_transformer_=Result.value)
        if len(responsible_user) == 0 or responsible_user[0] is None:
            raise ValueError(f"Responsible user not found: {responsible_user_tag}")
        from config.enums.users.roles import UserRolesEnum
        if responsible_user[0] < UserRolesEnum.CURATOR:
            raise ValueError("The responsible user of a procedure execution must be a curator.")

        for plate_tag in input_plates:
            self._validate_plate_constraints(procedure, plate_tag, "input")
        for plate_tag in output_plates:
            self._validate_plate_constraints(procedure, plate_tag, "output")

        # well identities are (plate, position) pairs: positions may repeat on different plates
        input_keys = {(self._well_plate(well, input_plates[0]), well.position) for well in execution.input_wells}
        output_keys = {(self._well_plate(well, output_plates[0]), well.position) for well in execution.output_wells}
        if len(output_keys) != len(execution.output_wells) or len(input_keys) != len(execution.input_wells):
            raise ValueError("Duplicate well positions (on the same plate) are not allowed.")
        for side, keys, plates in (("input", input_keys, input_plates), ("output", output_keys, output_plates)):
            unknown = sorted({f"{plate_tag}:{position}" for plate_tag, position in keys if plate_tag not in plates})
            if len(unknown) > 0:
                raise ValueError(f"Wells were given for plates that are not part of this execution: {', '.join(unknown)}")

        all_metrics = list(execution.output_well_metrics) + list(getattr(execution, "input_well_metrics") or [])
        metric_keys = [(getattr(metric, "plate_tag", None), metric.position, metric.trait_tag, metric.side)
                       for metric in all_metrics]

        if len(set(metric_keys)) != len(metric_keys):
            raise ValueError("Duplicate metrics (same well, trait and side) are not allowed.")
        metric_trait_tags = sorted({metric.trait_tag for metric in all_metrics})
        trait_attribute_tags = self._driver.execute_query(
            "UNWIND $trait_tags as trait_tag "
            "MATCH (t:Trait {tag : trait_tag}) "
            "RETURN t.tag as trait_tag, t.attribute_tag as attribute_tag",
            routing_="r", trait_tags=metric_trait_tags, result_transformer_=Result.data)
        trait_to_attribute = {row["trait_tag"]: row["attribute_tag"] for row in trait_attribute_tags}
        missing_traits = [trait_tag for trait_tag in metric_trait_tags if trait_tag not in trait_to_attribute]
        if len(missing_traits) > 0:
            raise ValueError(f"Traits not found: {', '.join(missing_traits)}")
        for metric in all_metrics:
            side_keys = output_keys if metric.side == "OUTPUT" else input_keys
            side_plates = output_plates if metric.side == "OUTPUT" else input_plates
            side_name = "output" if metric.side == "OUTPUT" else "input"
            metric_plate = getattr(metric, "plate_tag", None) or side_plates[0]
            if (metric_plate, metric.position) not in side_keys:
                raise ValueError(f"Metrics were given for a non-defined {side_name} well: "
                                 f"{metric_plate}:{metric.position}")
        if len(all_metrics) > 0:
            declared_attribute_tags = set(procedure.input_attribute_tags) | set(procedure.output_attribute_tags)
            undeclared_traits = [trait_tag for trait_tag, attribute_tag in trait_to_attribute.items()
                                 if attribute_tag not in declared_attribute_tags]
            if len(declared_attribute_tags) > 0 and len(undeclared_traits) > 0:
                raise ValueError(f"Metrics were given for traits that are not declared by the procedure: {', '.join(sorted(undeclared_traits))}")

        output_well_samples = {key: set() for key in output_keys}
        outputs_per_sample = {}
        for well in execution.input_wells:
            if len(well.sample_tags) == 0:
                raise ValueError(f"Input well {well.position} has no samples.")
            for output_ref in well.output_positions:
                output_plate_tag, output_position = split_well_ref(output_ref, output_plates[0])
                if (output_plate_tag, output_position) not in output_keys:
                    raise ValueError(f"Output well {output_ref} is not defined.")
                output_well_samples[(output_plate_tag, output_position)].update(well.sample_tags)
                for sample_tag in well.sample_tags:
                    outputs_per_sample.setdefault(sample_tag, set()).add((output_plate_tag, output_position))

        # the procedure declares how the run treats the sample numbers: mirroring (1 output well per
        # sample), a fixed or bounded N-fold duplication (e.g. N fractions) or anything in between
        min_outputs = procedure.min_output_wells_per_sample if procedure.min_output_wells_per_sample is not None else 1
        max_outputs = procedure.max_output_wells_per_sample
        for sample_tag, samples_outputs in sorted(outputs_per_sample.items()):
            if len(samples_outputs) < min_outputs:
                raise ValueError(f"Sample {sample_tag} is transferred to {len(samples_outputs)} output wells, but the "
                                 f"procedure requires at least {min_outputs} output wells per sample.")
            if max_outputs is not None and len(samples_outputs) > max_outputs:
                raise ValueError(f"Sample {sample_tag} is transferred to {len(samples_outputs)} output wells, but the "
                                 f"procedure requires at most {max_outputs} output wells per sample.")

        all_sample_tags = sorted({sample_tag for well in execution.input_wells for sample_tag in well.sample_tags})
        missing_samples = self._driver.execute_query(
            "UNWIND $sample_tags as sample_tag "
            "WITH sample_tag, EXISTS {(s:Sample {tag : sample_tag})} as exists "
            "WHERE NOT exists RETURN sample_tag",
            routing_="r", sample_tags=all_sample_tags, result_transformer_=Result.value)
        if len(missing_samples) > 0:
            raise ValueError(f"Samples not found: {', '.join(missing_samples)}")

        # the procedure may restrict its executions to submissions in a given state (e.g. SUBMITTED)
        if procedure.required_submission_state is not None:
            from config.enums.states import SubmissionStatesEnums
            required_state_tag = int(SubmissionStatesEnums[procedure.required_submission_state])
            wrong_state_submissions = self._driver.execute_query(
                "UNWIND $sample_tags as sample_tag "
                "MATCH (s:Submission)-[:HAS_SAMPLE]->(sample:Sample {tag : sample_tag}) "
                "OPTIONAL MATCH (s)-[:IN_STATE]->(state:State) "
                "WITH s, sample, collect(DISTINCT state.tag) as state_tags "
                "WHERE NOT $required_state_tag IN state_tags "
                "RETURN DISTINCT s.tag as submission_tag, state_tags",
                routing_="r", sample_tags=all_sample_tags, required_state_tag=required_state_tag,
                result_transformer_=Result.data)
            if len(wrong_state_submissions) > 0:
                raise ValueError("Submissions not in the state required by the procedure "
                                 f"({procedure.required_submission_state}): "
                                 + ", ".join(f"{row['submission_tag']} (state {', '.join(str(s) for s in row['state_tags'])})"
                                              for row in wrong_state_submissions))

        return {"responsible_user_tag": responsible_user_tag,
                "input_plates": input_plates,
                "output_plates": output_plates,
                "input_keys": input_keys,
                "output_keys": output_keys,
                "output_well_samples": output_well_samples,
                "all_metrics": all_metrics}

    def _validate_output_wells_free(self, output_plate_positions, exclude_execution_tag=None) -> None:
        """Only executions that are still running or that succeeded (or were explicitly kept blocked)
        occupy their output wells: failed or aborted runs free the wells for a re-run and drafts do
        not block anything until they start. `output_plate_positions` is a map of output plate tag to
        the positions used on it (multi-plate executions are checked per plate)."""
        if len(output_plate_positions) == 0:
            return
        exclude = ""
        if exclude_execution_tag is not None:
            exclude = "AND e.tag <> $exclude_tag "
        for output_plate_tag, positions in output_plate_positions.items():
            if len(positions) == 0:
                continue
            params = {"output_plate_tag": output_plate_tag, "positions": sorted(positions)}
            if exclude_execution_tag is not None:
                params["exclude_tag"] = exclude_execution_tag
            occupied_output_wells = self._driver.execute_query(
                "MATCH (e:ModularProcedureExecution)-[:HAS_WELL]->(w:ExecutionWell {side : 'OUTPUT'}) "
                "WHERE coalesce(w.plate_tag, e.output_plate_tag) = $output_plate_tag AND w.position IN $positions "
                f"{exclude}"
                "AND (coalesce(e.status, 'RUNNING') = 'RUNNING' OR "
                "coalesce(e.wells_blocked, coalesce(e.status, 'RUNNING') = 'SUCCEEDED')) "
                "RETURN collect(DISTINCT w.position) as occupied",
                routing_="r", parameters_=params, result_transformer_=Result.value)
            if len(occupied_output_wells) > 0 and len(occupied_output_wells[0]) > 0:
                raise ValueError(f"Output wells on {output_plate_tag} already used by another execution: "
                                 f"{', '.join(occupied_output_wells[0])}")

    def _store_execution_design(self, execution_tag: str, execution, design: dict, wells_blocked: bool) -> None:
        """Stores the plates, transfer map (input wells with samples and their output targets,
        output wells with their derived samples and condition applications) and the well metrics
        of an execution. Wipes any previously stored design first (used by draft saves)."""
        self._driver.execute_query(
            "MATCH (e:ModularProcedureExecution {tag : $execution_tag}) "
            "OPTIONAL MATCH (e)-[:HAS_WELL]->(w:ExecutionWell {execution_tag : $execution_tag}) "
            "OPTIONAL MATCH (w)-[:HAS_METRIC]->(m:ExecutionWellMetric {execution_tag : $execution_tag}) "
            "DETACH DELETE w, m "
            "SET e.input_plate_tag = $input_plate_tag, e.output_plate_tag = $output_plate_tag, "
            "e.input_plate_tags = $input_plate_tags, e.output_plate_tags = $output_plate_tags, "
            "e.responsible_user_tag = $responsible_user_tag, e.wells_blocked = $wells_blocked",
            routing_="w", execution_tag=execution_tag,
            input_plate_tag=design["input_plates"][0] if design["input_plates"] else None,
            output_plate_tag=design["output_plates"][0] if design["output_plates"] else None,
            input_plate_tags=design["input_plates"], output_plate_tags=design["output_plates"],
            responsible_user_tag=design["responsible_user_tag"], wells_blocked=wells_blocked)
        output_well_samples = design["output_well_samples"]

        for well in execution.input_wells:
            row_index, column_index = self._parse_position(well.position)
            plate_tag = self._well_plate(well, design["input_plates"][0])
            self._driver.execute_query(
                "MATCH (e:ModularProcedureExecution {tag : $execution_tag}) "
                "MERGE (w:ExecutionWell {execution_tag : $execution_tag, position : $position, "
                "plate_tag : $plate_tag, side : 'INPUT'}) "
                "SET w.row_index = $row_index, w.column_index = $column_index, "
                "w.output_positions = $output_positions "
                "MERGE (e)-[:HAS_WELL]->(w) "
                "WITH w "
                "MATCH (s:Sample) WHERE s.tag IN $sample_tags "
                "MERGE (s)-[:IN_WELL]->(w) ",
                routing_="w", execution_tag=execution_tag, position=well.position, plate_tag=plate_tag,
                row_index=row_index, column_index=column_index,
                output_positions=sorted(well.output_positions), sample_tags=sorted(well.sample_tags))

        for well in execution.output_wells:
            row_index, column_index = self._parse_position(well.position)
            plate_tag = self._well_plate(well, design["output_plates"][0])
            self._driver.execute_query(
                "MATCH (e:ModularProcedureExecution {tag : $execution_tag}) "
                "MERGE (w:ExecutionWell {execution_tag : $execution_tag, position : $position, "
                "plate_tag : $plate_tag, side : 'OUTPUT'}) "
                "SET w.row_index = $row_index, w.column_index = $column_index "
                "MERGE (e)-[:HAS_WELL]->(w) "
                "WITH w "
                "MATCH (s:Sample) WHERE s.tag IN $sample_tags "
                "MERGE (s)-[:IN_WELL]->(w) ",
                routing_="w", execution_tag=execution_tag, position=well.position, plate_tag=plate_tag,
                row_index=row_index, column_index=column_index,
                sample_tags=sorted(output_well_samples[(plate_tag, well.position)]))
            for ca_tag in well.condition_application_tags:
                self._driver.execute_query(
                    "MATCH (w:ExecutionWell {execution_tag : $execution_tag, position : $position, "
                    "plate_tag : $plate_tag, side : 'OUTPUT'}) "
                    "MATCH (c:ConditionApplication {tag : $ca_tag}) "
                    "MERGE (w)-[:HAS_APPLICATION]->(c) ",
                    routing_="w", execution_tag=execution_tag, position=well.position,
                    plate_tag=plate_tag, ca_tag=ca_tag)

        for metric in design["all_metrics"]:
            primary_side_plates = design["output_plates"] if metric.side == "OUTPUT" else design["input_plates"]
            metric_plate = getattr(metric, "plate_tag", None) or primary_side_plates[0]
            self._driver.execute_query(
                "MATCH (e:ModularProcedureExecution {tag : $execution_tag})-[:HAS_WELL]->"
                "(w:ExecutionWell {execution_tag : $execution_tag, position : $position, "
                "plate_tag : $plate_tag, side : $side}) "
                "MATCH (t:Trait {tag : $trait_tag}) "
                "MERGE (m:ExecutionWellMetric {execution_tag : $execution_tag, position : $position, "
                "plate_tag : $plate_tag, trait_tag : $trait_tag, side : $side}) "
                "SET m.value = $value, m.created_at = timestamp() "
                "MERGE (w)-[:HAS_METRIC]->(m) "
                "MERGE (m)-[:INSTANCE_OF]->(t) "
                "WITH m, t "
                "MERGE (a:Attribute {tag : t.attribute_tag}) "
                "MERGE (m)-[:OF_ATTRIBUTE]->(a) ",
                routing_="w", execution_tag=execution_tag, position=metric.position,
                plate_tag=metric_plate, side=metric.side,
                trait_tag=metric.trait_tag, value=metric.value)

    def _design_from_stored_execution(self, execution):
        """Presents the stored design of an execution in the shape the design validation expects."""
        from config.models.procedures import InsertProcedureExecutionModel, ExecutionWellMetricModel
        input_metrics = list(execution.input_well_metrics or [])
        input_metrics += [metric for well in execution.input_wells for metric in (getattr(well, "metrics", None) or [])]
        output_metrics = [metric for well in execution.output_wells for metric in (well.metrics or [])]
        def _with_side(metric, side):
            return metric if getattr(metric, "side", None) else metric.model_copy(update={"side": side})
        def _primary(side):
            tags = list(getattr(execution, f"{side}_plate_tags", None) or [])
            if len(tags) == 0 and getattr(execution, f"{side}_plate_tag", None) is not None:
                tags = [getattr(execution, f"{side}_plate_tag")]
            return tags[0] if len(tags) > 0 else None
        def _stored_plate(well, side):
            # wells of legacy single-plate executions carry no plate tag: they are on the primary plate
            return getattr(well, "plate_tag", None) or _primary(side)
        return InsertProcedureExecutionModel(
            input_plate_tag=_primary("input"),
            output_plate_tag=_primary("output"),
            additional_input_plate_tags=[tag for tag in (getattr(execution, "input_plate_tags", None) or [])
                                         if tag != (_primary("input"))],
            additional_output_plate_tags=[tag for tag in (getattr(execution, "output_plate_tags", None) or [])
                                         if tag != (_primary("output"))],
            responsible_user_tag=execution.responsible_user_tag,
            input_wells=[{"position": w.position, "plate_tag": _stored_plate(w, "input"),
                          "sample_tags": list(w.sample_tags),
                          "output_positions": list(w.output_positions)} for w in execution.input_wells],
            output_wells=[{"position": w.position, "plate_tag": _stored_plate(w, "output"),
                           "sample_tags": list(w.sample_tags),
                           "condition_application_tags": list(w.condition_application_tags)}
                          for w in execution.output_wells],
            input_well_metrics=[_with_side(m, "INPUT") for m in input_metrics],
            output_well_metrics=[_with_side(m, "OUTPUT") for m in output_metrics],
        )

    def get_occupied_output_wells(self, plate_tag: str) -> List[str]:
        """Returns the positions of the plate's output wells that are blocked by executions of
        modular procedures (still running or kept blocked): the wells an execution setup must not
        map its outputs onto. Drafts and finished-unblocked executions do not block anything."""
        if plate_tag is None:
            return []
        rows = self._driver.execute_query(
            "MATCH (e:ModularProcedureExecution)-[:HAS_WELL]->(w:ExecutionWell {side : 'OUTPUT'}) "
            "WHERE coalesce(w.plate_tag, e.output_plate_tag) = $plate_tag "
            "AND (coalesce(e.status, 'RUNNING') = 'RUNNING' OR "
            "coalesce(e.wells_blocked, coalesce(e.status, 'RUNNING') = 'SUCCEEDED')) "
            "RETURN collect(DISTINCT w.position) as occupied",
            routing_="r", plate_tag=plate_tag, result_transformer_=Result.value)
        return rows[0] if len(rows) > 0 and rows[0] is not None else []

    def get_draft_executions_wells(self, plate_tag: str) -> Dict[str, List[str]]:
        """Returns a map of the plate's well positions to the tags of the DRAFT executions that
        use them (input or output side). Drafts block nothing — publishing this map lets the
        setup pages warn about potential conflicts between parallel drafts of several curators
        (only the execution that starts first gets the wells)."""
        if plate_tag is None:
            return {}
        rows = self._driver.execute_query(
            "MATCH (e:ModularProcedureExecution {status : 'DRAFT'})-[:HAS_WELL]->(w:ExecutionWell) "
            "WHERE ((w.side = 'INPUT' AND coalesce(w.plate_tag, e.input_plate_tag) = $plate_tag) OR "
            "(w.side = 'OUTPUT' AND coalesce(w.plate_tag, e.output_plate_tag) = $plate_tag)) "
            "RETURN w.position AS position, collect(DISTINCT e.tag) AS draft_tags "
            "ORDER BY w.position",
            routing_="r", plate_tag=plate_tag, result_transformer_=Result.data)
        return {row["position"]: list(row["draft_tags"]) for row in rows}

    def execute(self, tag: str, execution, user_tag: str) -> "ProcedureExecutionModel":
        """Starts a published modular procedure execution as a run: the execution is validated
        (design + output well occupancy), created directly in the RUNNING state with an
        execution-tag hash and starts blocking its output wells; the submissions are only freed
        when the execution is confirmed via finish_execution."""
        from config.models.procedures import ProcedureExecutionModel
        procedure = self.get(tag=tag)
        if procedure.status != "PUBLISHED":
            raise ValueError(f"Only published modular procedures can be executed - this procedure is in state {procedure.status}.")
        design = self._validate_execution_design(procedure, execution, user_tag)
        self._validate_output_wells_free(self._group_by_plate(design["output_keys"]))
        content = {
            "procedure_tag": tag,
            "input_plate_tags": design["input_plates"],
            "output_plate_tags": design["output_plates"],
            "input_wells": [{"position": w.position, "plate_tag": self._well_plate(w, design["input_plates"][0]),
                             "sample_tags": sorted(w.sample_tags),
                             "output_positions": sorted(w.output_positions)} for w in execution.input_wells],
            "output_wells": [{"position": w.position, "plate_tag": self._well_plate(w, design["output_plates"][0]),
                              "condition_application_tags": sorted(w.condition_application_tags)} for w in execution.output_wells],
        }
        # the creation time is part of the hash so the same transfer map can legitimately be
        # re-run (e.g. after a failed or aborted execution); the occupancy rule above is what
        # actually protects wells from being overwritten concurrently
        execution_tag = hashlib.sha256(json.dumps(
            {**content, "created_at": time.time()}, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:24]

        self._driver.execute_query(
            "MATCH (m:ModularProcedure {tag : $procedure_tag}) MATCH (u:User {tag : $user_tag}) "
            "MERGE (e:ModularProcedureExecution {tag : $execution_tag}) "
            "SET e.created_at = timestamp(), e += $props "
            "MERGE (m)-[:WAS_EXECUTED]->(e) "
            "MERGE (u)-[:EXECUTED]->(e) ",
            routing_="w", procedure_tag=tag, user_tag=user_tag, execution_tag=execution_tag,
            props={"procedure_tag": tag, "input_plate_tag": design["input_plates"][0],
                   "output_plate_tag": design["output_plates"][0],
                   "input_plate_tags": design["input_plates"], "output_plate_tags": design["output_plates"],
                   "user_tag": user_tag,
                   "responsible_user_tag": design["responsible_user_tag"], "status": "RUNNING",
                   "wells_blocked": True})
        self._store_execution_design(execution_tag, execution, design, wells_blocked=True)
        self._set_execution_state(execution_tag=execution_tag, state="RUNNING", user_tag=user_tag)
        return self.get_execution(execution_tag=execution_tag)

    def create_execution_draft(self, tag: str, user_tag: str) -> "ProcedureExecutionModel":
        """Creates an empty DRAFT execution of a published modular procedure with a
        backend-generated ID: the design (plates, sample placement, transfer map, values) can be
        saved and continued later without blocking anything — see update_execution_draft. The
        run starts (and is fully validated incl. the output well occupancy) via start_execution."""
        import uuid
        procedure = self.get(tag=tag)
        if procedure.status != "PUBLISHED":
            raise ValueError(f"Only published modular procedures can be executed - this procedure is in state {procedure.status}.")
        execution_tag = "exec_" + uuid.uuid4().hex[:20]
        self._driver.execute_query(
            "MATCH (m:ModularProcedure {tag : $procedure_tag}) MATCH (u:User {tag : $user_tag}) "
            "MERGE (e:ModularProcedureExecution {tag : $execution_tag}) "
            "SET e.created_at = timestamp(), e += $props "
            "MERGE (m)-[:WAS_EXECUTED]->(e) "
            "MERGE (u)-[:EXECUTED]->(e) ",
            routing_="w", procedure_tag=tag, user_tag=user_tag, execution_tag=execution_tag,
            props={"procedure_tag": tag, "input_plate_tag": None, "output_plate_tag": None,
                   "input_plate_tags": [], "output_plate_tags": [],
                   "user_tag": user_tag, "responsible_user_tag": user_tag, "status": "DRAFT",
                   "wells_blocked": False})
        self._set_execution_state(execution_tag=execution_tag, state="DRAFT", user_tag=user_tag)
        return self.get_execution(execution_tag=execution_tag)

    def update_execution_draft(self, execution_tag: str, design_update, user_tag: str) -> "ProcedureExecutionModel":
        """Saves the setup of a DRAFT execution (the current design is replaced wholesale): plates,
        responsible user, sample placement, transfer map, condition applications and per-well
        values. The design must be valid on its own (existing plates/samples/traits, unique
        positions, every transfer target defined, declared sample numbers) but the output wells do
        not block anything yet — the occupancy is checked when the execution starts."""
        execution = self.get_execution(execution_tag=execution_tag)
        if execution.status != "DRAFT":
            raise ValueError("Only draft executions can be set up — a started execution is immutable.")
        procedure = self.get(tag=execution.procedure_tag)
        design = self._validate_execution_design(procedure, design_update, user_tag)
        self._store_execution_design(execution_tag, design_update, design, wells_blocked=False)
        return self.get_execution(execution_tag=execution_tag)

    def start_execution(self, execution_tag: str, user_tag: str) -> "ProcedureExecutionModel":
        """Starts a saved DRAFT execution as a run: the stored design is validated again in full —
        including the output well occupancy, which drafts do not block until they start — and the
        execution moves to RUNNING, blocking its output wells."""
        execution = self.get_execution(execution_tag=execution_tag)
        if execution.status != "DRAFT":
            raise ValueError("Only draft executions can be started.")
        if len(execution.input_wells) == 0 or len(execution.output_wells) == 0:
            raise ValueError("The draft has no design yet — save the plates, samples and transfer map first.")
        procedure = self.get(tag=execution.procedure_tag)
        if procedure.status != "PUBLISHED":
            raise ValueError(f"Only published modular procedures can be executed - this procedure is in state {procedure.status}.")
        design_update = self._design_from_stored_execution(execution)
        design = self._validate_execution_design(procedure, design_update, user_tag)
        self._validate_output_wells_free(self._group_by_plate(design["output_keys"]),
                                         exclude_execution_tag=execution_tag)
        self._driver.execute_query(
            "MATCH (e:ModularProcedureExecution {tag : $execution_tag}) "
            "SET e.status = 'RUNNING', e.wells_blocked = true, e.user_tag = $user_tag, "
            "e.responsible_user_tag = coalesce(e.responsible_user_tag, $user_tag)",
            routing_="w", execution_tag=execution_tag, user_tag=user_tag)
        self._set_execution_state(execution_tag=execution_tag, state="RUNNING", user_tag=user_tag)
        return self.get_execution(execution_tag=execution_tag)

    def delete_execution_draft(self, execution_tag: str, user_tag: str) -> bool:
        """Deletes a DRAFT execution (and only a draft). Drafts are setup work, not recorded
        facility history: unlike started executions they can be removed again."""
        execution = self.get_execution(execution_tag=execution_tag)
        if execution.status != "DRAFT":
            raise ValueError("Only draft executions can be deleted — a started execution is part of the recorded history.")
        self._driver.execute_query(
            "MATCH (e:ModularProcedureExecution {tag : $execution_tag}) "
            "OPTIONAL MATCH (e)-[:HAS_WELL]->(w:ExecutionWell {execution_tag : $execution_tag}) "
            "OPTIONAL MATCH (w)-[:HAS_METRIC]->(m:ExecutionWellMetric {execution_tag : $execution_tag}) "
            "DETACH DELETE e, w, m",
            routing_="w", execution_tag=execution_tag)
        self._driver.execute_query(
            "MATCH (e:ModularProcedureExecution {tag : $execution_tag})-[r:IN_STATE]->() DELETE r",
            routing_="w", execution_tag=execution_tag)
        return True

    def finish_execution(self, execution_tag: str, outcome: str, user_tag: str, comment: str = None,
                         block_output_wells: bool = None) -> "ProcedureExecutionModel":
        """Transitions a procedure execution to the given state (SUCCEEDED, FAILED or ABORTED).
        Leaving the RUNNING state always frees the submissions owning the placed samples in the
        procedure (they stay where they are physically, but are freed for the next module). A
        transition to SUCCEEDED applies the success effects; finished executions can be corrected
        later (e.g. FAILED to SUCCEEDED) — every state is recorded in the IN_STATE history.
        block_output_wells overrides whether the output wells stay blocked after the change (e.g.
        an aborted robot run with dirty wells must stay blocked); omitted it defaults to the
        outcome (SUCCEEDED blocks, FAILED/ABORTED release the wells for a re-run)."""
        wells_blocked = block_output_wells if block_output_wells is not None else (outcome == "SUCCEEDED")
        from config.models.procedures import ProcedureExecutionModel
        if outcome not in ("SUCCEEDED", "FAILED", "ABORTED"):
            raise ValueError("Outcome must be SUCCEEDED, FAILED or ABORTED.")
        execution = self.get_execution(execution_tag=execution_tag)
        current_state = self.get_current_execution_state(execution)
        if outcome == "RUNNING" or outcome == current_state:
            raise ValueError(f"This procedure execution is already in state {current_state}.")
        if current_state == "DRAFT":
            raise ValueError("This procedure execution is still a draft — start it before confirming an outcome.")
        procedure = self.get(tag=execution.procedure_tag)

        if current_state != "RUNNING":
            self._set_execution_state(execution_tag=execution_tag, state=outcome, user_tag=user_tag)
            self._driver.execute_query(
                "MATCH (e:ModularProcedureExecution {tag : $execution_tag}) "
                "SET e.finished_at = $finished_at, e.finished_by = $user_tag, e.finish_comment = $comment, "
                "e.wells_blocked = $wells_blocked",
                routing_="w", execution_tag=execution_tag, wells_blocked=wells_blocked,
                finished_at=time.time(), user_tag=user_tag, comment=comment)
            if outcome == "SUCCEEDED":
                self._apply_success(execution_tag=execution_tag, procedure=procedure, user_tag=user_tag)
            return self.get_execution(execution_tag=execution_tag)

        done_submission_tags = self._driver.execute_query(
            "MATCH (e:ModularProcedureExecution {tag : $execution_tag})-[:HAS_WELL]->"
            "(w:ExecutionWell {execution_tag : $execution_tag, side : 'INPUT'}) "
            "MATCH (s:Sample)-[:IN_WELL]->(w)<-[:HAS_SAMPLE]-(sub:Submission) "
            "MATCH (sub)-[r:IN_PROCEDURE]->(m:ModularProcedure {tag : $procedure_tag}) "
            "SET r.done = true, r.done_at = $done_at, r.done_by = $user_tag "
            "RETURN collect(DISTINCT sub.tag) as done_submissions",
            routing_="w", execution_tag=execution_tag, procedure_tag=procedure.tag,
            user_tag=user_tag, done_at=time.time(), result_transformer_=Result.value)
        done_submissions = done_submission_tags[0] if len(done_submission_tags) > 0 else []

        if outcome == "SUCCEEDED" and len(done_submissions) > 0:
            self._apply_success(execution_tag=execution_tag, procedure=procedure, user_tag=user_tag,
                                submission_tags=done_submissions)

        self._set_execution_state(execution_tag=execution_tag, state=outcome, user_tag=user_tag)
        self._driver.execute_query(
            "MATCH (e:ModularProcedureExecution {tag : $execution_tag}) "
            "SET e.finished_at = $finished_at, e.finished_by = $user_tag, "
            "e.finish_comment = $comment, e.done_submission_tags = $done_submissions, "
            "e.wells_blocked = $wells_blocked",
            routing_="w", execution_tag=execution_tag, wells_blocked=wells_blocked,
            finished_at=time.time(), user_tag=user_tag, comment=comment, done_submissions=done_submissions)

        return self.get_execution(execution_tag=execution_tag)

    def _apply_success(self, execution_tag: str, procedure, user_tag: str, submission_tags: List[str] = None) -> None:
        """Applies the success effects to the submissions owning the placed samples: they adopt the
        condition applications (procedure level and per output well) and get the optional success
        submission state. No-op if the execution placed no samples."""
        if submission_tags is None:
            submission_tags = self._driver.execute_query(
                "MATCH (e:ModularProcedureExecution {tag : $execution_tag})-[:HAS_WELL]->"
                "(w:ExecutionWell {execution_tag : $execution_tag, side : 'INPUT'}) "
                "MATCH (s:Sample)-[:IN_WELL]->(w)<-[:HAS_SAMPLE]-(sub:Submission) "
                "RETURN collect(DISTINCT sub.tag) as submissions",
                routing_="r", execution_tag=execution_tag, result_transformer_=Result.value)
            submission_tags = submission_tags[0] if len(submission_tags) > 0 else []
        if len(submission_tags) == 0:
            return
        self._driver.execute_query(
            "MATCH (m:ModularProcedure {tag : $procedure_tag})-[:HAS_CONDITION_APPLICATION]->(c:ConditionApplication) "
            "MATCH (sub:Submission) WHERE sub.tag IN $submission_tags "
            "MERGE (sub)-[r:HAS_APPLICATION]->(c) "
            "SET r.created_at = timestamp() ",
            routing_="w", procedure_tag=procedure.tag, submission_tags=submission_tags)
        self._driver.execute_query(
            "MATCH (e:ModularProcedureExecution {tag : $execution_tag})-[:HAS_WELL]->"
            "(w:ExecutionWell {execution_tag : $execution_tag, side : 'OUTPUT'}) "
            "MATCH (w)-[:HAS_APPLICATION]->(c:ConditionApplication) "
            "MATCH (s:Sample)-[:IN_WELL]->(w)<-[:HAS_SAMPLE]-(sub:Submission) "
            "WHERE sub.tag IN $submission_tags "
            "MERGE (sub)-[r:HAS_APPLICATION]->(c) "
            "SET r.created_at = timestamp() ",
            routing_="w", execution_tag=execution_tag, submission_tags=submission_tags)
        if procedure.success_submission_state is not None:
            from config.enums.states import SubmissionStatesEnums
            new_state = SubmissionStatesEnums[procedure.success_submission_state]
            self._driver.execute_query(
                "MATCH (sub:Submission) WHERE sub.tag IN $submission_tags "
                "MATCH (state:State {tag : $new_state}) "
                "CREATE (sub)-[r:IN_STATE]->(state) "
                "SET r.created_at = timestamp(), r.user_tag = $user_tag ",
                routing_="w", submission_tags=submission_tags,
                new_state=new_state.value, user_tag=user_tag)
            # like Submission.update_state: a state change can affect the submission scope of
            # every user (e.g. a success state of PUBLISHED), so the scope cache must be cleared
            invalidate_all_cached_scopes()

    def get_execution(self, execution_tag: str) -> "ProcedureExecutionModel":
        "Returns the procedure execution by its tag."
        from config.models.procedures import ProcedureExecutionModel
        execution_exists = self._driver.execute_query(
            "WITH EXISTS {(e:ModularProcedureExecution {tag : $execution_tag})} as exists RETURN exists",
            routing_="r", execution_tag=execution_tag, result_transformer_=Result.value)
        if len(execution_exists) == 0 or not execution_exists[0]:
            raise KeyError("Procedure execution not found.")

        input_wells = self._driver.execute_query(
            "MATCH (e:ModularProcedureExecution {tag : $execution_tag})-[:HAS_WELL]->(w:ExecutionWell {side : 'INPUT'}) "
            "OPTIONAL MATCH (s:Sample)-[:IN_WELL]->(w) "
            "OPTIONAL MATCH (w)-[:HAS_METRIC]->(m:ExecutionWellMetric)-[:INSTANCE_OF]->(t:Trait) "
            "WITH w, collect(DISTINCT s.tag) as sample_tags, "
            "collect(CASE WHEN m IS NULL THEN NULL ELSE "
            "{trait_tag: t.tag, attribute_tag: t.attribute_tag, value: m.value} END) as metrics "
            "RETURN {position: w.position, plate_tag: w.plate_tag, row_index: w.row_index, "
            "column_index: w.column_index, "
            "sample_tags: [tag IN sample_tags WHERE tag IS NOT NULL], output_positions: w.output_positions, "
            "metrics: [metric IN metrics WHERE metric IS NOT NULL]} as well "
            "ORDER BY w.plate_tag, w.row_index, w.column_index",
            routing_="r", execution_tag=execution_tag, result_transformer_=Result.data)
        output_wells = self._driver.execute_query(
            "MATCH (e:ModularProcedureExecution {tag : $execution_tag})-[:HAS_WELL]->(w:ExecutionWell {side : 'OUTPUT'}) "
            "OPTIONAL MATCH (s:Sample)-[:IN_WELL]->(w) "
            "OPTIONAL MATCH (w)-[:HAS_APPLICATION]->(c:ConditionApplication) "
            "OPTIONAL MATCH (w)-[:HAS_METRIC]->(m:ExecutionWellMetric)-[:INSTANCE_OF]->(t:Trait) "
            "WITH w, collect(DISTINCT s.tag) as sample_tags, collect(DISTINCT c.tag) as ca_tags, "
            "collect(CASE WHEN m IS NULL THEN NULL ELSE "
            "{trait_tag: t.tag, attribute_tag: t.attribute_tag, value: m.value} END) as metrics "
            "RETURN {position: w.position, plate_tag: w.plate_tag, row_index: w.row_index, "
            "column_index: w.column_index, "
            "sample_tags: sample_tags, condition_application_tags: ca_tags, "
            "metrics: [metric IN metrics WHERE metric IS NOT NULL]} as well "
            "ORDER BY w.plate_tag, w.row_index, w.column_index",
            routing_="r", execution_tag=execution_tag, result_transformer_=Result.data)

        return self._assemble_execution(execution_tag=execution_tag,
                                        input_wells=[row["well"] for row in input_wells],
                                        output_wells=[row["well"] for row in output_wells])

    def _assemble_execution(self, execution_tag: str, input_wells: list, output_wells: list) -> "ProcedureExecutionModel":
        "Assembles a ProcedureExecutionModel from the stored well rows."
        from config.models.procedures import (
            ProcedureExecutionModel,
            ProcedureExecutionInputWellModel,
            ProcedureExecutionOutputWellModel,
        )
        head = self._driver.execute_query(
            "MATCH (e:ModularProcedureExecution {tag : $execution_tag}) "
            "RETURN {tag: e.tag, procedure_tag: e.procedure_tag, "
            "input_plate_tags: coalesce(e.input_plate_tags, CASE WHEN e.input_plate_tag IS NULL THEN [] ELSE [e.input_plate_tag] END), "
            "output_plate_tags: coalesce(e.output_plate_tags, CASE WHEN e.output_plate_tag IS NULL THEN [] ELSE [e.output_plate_tag] END), "
            "input_plate_tag: e.input_plate_tag, "
            "output_plate_tag: e.output_plate_tag, user_tag: e.user_tag, "
            "responsible_user_tag: e.responsible_user_tag, created_at: e.created_at, "
            "status: e.status, wells_blocked: coalesce(e.wells_blocked, true), "
            "finished_at: e.finished_at, finished_by: e.finished_by, "
            "finish_comment: e.finish_comment, done_submission_tags: coalesce(e.done_submission_tags, [])} as execution",
            routing_="r", execution_tag=execution_tag, result_transformer_=Result.data)
        execution = head[0]["execution"]
        execution["input_wells"] = [ProcedureExecutionInputWellModel(**well) for well in input_wells]
        execution["output_wells"] = [ProcedureExecutionOutputWellModel(**well) for well in output_wells]
        return ProcedureExecutionModel(**execution)

    def find_execution_tags(self, status: str = None, limit: int = None) -> List[str]:
        """Returns the tags of all procedure executions, newest first, optionally filtered by
        their current state."""
        params = {"limit": limit}
        query = "MATCH (e:ModularProcedureExecution) "
        if status is not None:
            query += ("WHERE coalesce(e.status, 'RUNNING') = $status ")
            params["status"] = status
        query += "RETURN e.tag as tag ORDER BY e.created_at DESC"
        if limit is not None:
            query += " LIMIT $limit"
        return self._driver.execute_query(query, routing_="r", parameters_=params, result_transformer_=Result.value)

    def get_executions(self, tag: str) -> List[str]:
        "Returns the tags of the executions of the given procedure."
        if not self.exists(tag=tag):
            raise KeyError("Modular procedure not found.")
        return self._driver.execute_query(
            "MATCH (e:ModularProcedureExecution {procedure_tag : $tag}) "
            "RETURN e.tag as tag ORDER BY e.created_at ASC",
            routing_="r", tag=tag, result_transformer_=Result.value)

    def set_execution_metrics(self, execution_tag: str, well_metrics, user_tag: str) -> "ProcedureExecutionModel":
        """Sets or updates the measured attribute values (metrics) of an execution's wells: the
        result values of the declared attributes are often only readable after the run, so this
        is available for RUNNING and SUCCEEDED executions (drafts enter their values via the
        draft save)."""
        execution = self.get_execution(execution_tag=execution_tag)
        if execution.status not in ("RUNNING", "SUCCEEDED"):
            raise ValueError("Measured values can only be recorded for a running or successfully finished execution.")
        execution_exists = self._driver.execute_query(
            "WITH EXISTS {(e:ModularProcedureExecution {tag : $execution_tag})} as exists RETURN exists",
            routing_="r", execution_tag=execution_tag, result_transformer_=Result.value)
        if len(execution_exists) == 0 or not execution_exists[0]:
            raise KeyError("Procedure execution not found.")

        metric_keys = [(getattr(metric, "plate_tag", None), metric.position, metric.trait_tag, metric.side)
                       for metric in well_metrics]
        if len(set(metric_keys)) != len(metric_keys):
            raise ValueError("Duplicate metrics (same well, trait and side) are not allowed.")
        for metric in well_metrics:
            if metric.side not in ("INPUT", "OUTPUT"):
                raise ValueError(f"Invalid metric side: {metric.side}")
        existing_positions = self._driver.execute_query(
            "MATCH (e:ModularProcedureExecution {tag : $execution_tag})-[:HAS_WELL]->(w:ExecutionWell) "
            "WHERE w.position IN $positions "
            "RETURN collect({position: w.position, plate_tag: w.plate_tag, side: w.side}) as wells",
            routing_="r", execution_tag=execution_tag,
            positions=sorted({metric.position for metric in well_metrics}), result_transformer_=Result.value)
        plates = self._driver.execute_query(
            "MATCH (e:ModularProcedureExecution {tag : $execution_tag}) "
            "RETURN {input: coalesce(e.input_plate_tags, CASE WHEN e.input_plate_tag IS NULL THEN [] "
            "ELSE [e.input_plate_tag] END), output: coalesce(e.output_plate_tags, "
            "CASE WHEN e.output_plate_tag IS NULL THEN [] ELSE [e.output_plate_tag] END)} as plates",
            routing_="r", execution_tag=execution_tag, result_transformer_=Result.value)
        primary_plates = plates[0] if len(plates) > 0 else {}
        def _metric_plate(metric):
            side_key = "input" if metric.side == "INPUT" else "output"
            side_plates = list((primary_plates or {}).get(side_key) or [])
            if len(side_plates) == 0:
                return None
            return getattr(metric, "plate_tag", None) or side_plates[0]
        existing = {(w.get("plate_tag") or (primary_plates or {}).get(
                        "input" if w["side"] == "INPUT" else "output"), w["position"], w["side"])
                    for w in (existing_positions[0] if existing_positions else [])}
        missing = [f"{_metric_plate(metric)}:{metric.position} ({metric.side})" for metric in well_metrics
                   if (_metric_plate(metric), metric.position, metric.side) not in existing]
        if len(missing) > 0:
            raise ValueError(f"Metrics were given for wells that do not exist on that side of this execution: {', '.join(missing)}")

        trait_tags = sorted({metric.trait_tag for metric in well_metrics})
        found_traits = self._driver.execute_query(
            "UNWIND $trait_tags as trait_tag MATCH (t:Trait {tag : trait_tag}) RETURN collect(t.tag) as traits",
            routing_="r", trait_tags=trait_tags, result_transformer_=Result.value)
        found = found_traits[0] if len(found_traits) > 0 else []
        missing_traits = [trait_tag for trait_tag in trait_tags if trait_tag not in found]
        if len(missing_traits) > 0:
            raise ValueError(f"Traits not found: {', '.join(missing_traits)}")

        for metric in well_metrics:
            self._driver.execute_query(
                "MATCH (e:ModularProcedureExecution {tag : $execution_tag})-[:HAS_WELL]->"
                "(w:ExecutionWell {execution_tag : $execution_tag, position : $position, "
                "plate_tag : $plate_tag, side : $side}) "
                "MATCH (t:Trait {tag : $trait_tag}) "
                "MERGE (m:ExecutionWellMetric {execution_tag : $execution_tag, position : $position, "
                "plate_tag : $plate_tag, trait_tag : $trait_tag, side : $side}) "
                "SET m.value = $value, m.created_at = timestamp(), m.user_tag = $user_tag "
                "MERGE (w)-[:HAS_METRIC]->(m) "
                "MERGE (m)-[:INSTANCE_OF]->(t) "
                "WITH m, t "
                "MERGE (a:Attribute {tag : t.attribute_tag}) "
                "MERGE (m)-[:OF_ATTRIBUTE]->(a) ",
                routing_="w", execution_tag=execution_tag, position=metric.position,
                plate_tag=_metric_plate(metric), side=metric.side,
                trait_tag=metric.trait_tag, value=metric.value)
        return self.get_execution(execution_tag=execution_tag)

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
            "version: m.version, lineage_tag: m.lineage_tag, content_hash: m.content_hash, user_tag: m.user_tag, "
            "created_at: m.created_at, published_at: m.published_at, "
            "condition_application_tags: ca_tags, protocol_tags: protocol_tags} as procedure"
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
        }
        r = self._driver.execute_query(query, routing_="w", tag=new_tag, user_tag=user_tag,
                                       parent_tag=tag, props=props, result_transformer_=Result.value)
        if len(r) == 0 or r[0] is None:
            raise ValueError("Modular procedure version could not be created.")

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

    def execute(self, tag: str, execution, user_tag: str) -> "ProcedureExecutionModel":
        "Executes a published modular procedure on a set of samples and marks the affected submissions as done."
        from config.models.procedures import ProcedureExecutionModel
        procedure = self.get(tag=tag)
        if procedure.status != "PUBLISHED":
            raise ValueError("Only published modular procedures can be executed.")

        for plate_tag in [execution.input_plate_tag, execution.output_plate_tag]:
            plate_exists = self._driver.execute_query(
                "WITH EXISTS {(p:Plate {tag : $plate_tag})} as exists RETURN exists",
                routing_="r", plate_tag=plate_tag, result_transformer_=Result.value)
            if len(plate_exists) == 0 or not plate_exists[0]:
                raise ValueError(f"Plate not found: {plate_tag}")

        output_positions = {well.position for well in execution.output_wells}
        input_positions = {well.position for well in execution.input_wells}
        if len(output_positions) != len(execution.output_wells) or len(input_positions) != len(execution.input_wells):
            raise ValueError("Duplicate well positions are not allowed.")

        output_well_samples = {position: set() for position in output_positions}
        for well in execution.input_wells:
            if len(well.sample_tags) == 0:
                raise ValueError(f"Input well {well.position} has no samples.")
            for output_position in well.output_positions:
                if output_position not in output_positions:
                    raise ValueError(f"Output well {output_position} is not defined.")
                output_well_samples[output_position].update(well.sample_tags)

        occupied_output_wells = self._driver.execute_query(
            "MATCH (e:ModularProcedureExecution)-[:HAS_WELL]->(w:ExecutionWell {side : 'OUTPUT'}) "
            "WHERE e.output_plate_tag = $output_plate_tag AND w.position IN $positions "
            "RETURN collect(DISTINCT w.position) as occupied",
            routing_="r", output_plate_tag=execution.output_plate_tag,
            positions=sorted(output_positions), result_transformer_=Result.value)
        if len(occupied_output_wells) > 0 and len(occupied_output_wells[0]) > 0:
            raise ValueError(f"Output wells already used by another execution: {', '.join(occupied_output_wells[0])}")

        all_sample_tags = sorted({sample_tag for well in execution.input_wells for sample_tag in well.sample_tags})
        missing_samples = self._driver.execute_query(
            "UNWIND $sample_tags as sample_tag "
            "WITH sample_tag, EXISTS {(s:Sample {tag : sample_tag})} as exists "
            "WHERE NOT exists RETURN sample_tag",
            routing_="r", sample_tags=all_sample_tags, result_transformer_=Result.value)
        if len(missing_samples) > 0:
            raise ValueError(f"Samples not found: {', '.join(missing_samples)}")

        content = {
            "procedure_tag": tag,
            "input_plate_tag": execution.input_plate_tag,
            "output_plate_tag": execution.output_plate_tag,
            "input_wells": [{"position": w.position, "sample_tags": sorted(w.sample_tags),
                             "output_positions": sorted(w.output_positions)} for w in execution.input_wells],
            "output_wells": [{"position": w.position,
                              "condition_application_tags": sorted(w.condition_application_tags)} for w in execution.output_wells],
        }
        execution_tag = hashlib.sha256(json.dumps(content, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:24]
        execution_exists = self._driver.execute_query(
            "WITH EXISTS {(e:ModularProcedureExecution {tag : $execution_tag})} as exists RETURN exists",
            routing_="r", execution_tag=execution_tag, result_transformer_=Result.value)
        if len(execution_exists) > 0 and execution_exists[0]:
            raise ValueError("An identical procedure execution already exists.")

        self._driver.execute_query(
            "MATCH (m:ModularProcedure {tag : $procedure_tag}) MATCH (u:User {tag : $user_tag}) "
            "MERGE (e:ModularProcedureExecution {tag : $execution_tag}) "
            "SET e.created_at = timestamp(), e += $props "
            "MERGE (m)-[:WAS_EXECUTED]->(e) "
            "MERGE (u)-[:EXECUTED]->(e) ",
            routing_="w", procedure_tag=tag, user_tag=user_tag, execution_tag=execution_tag,
            props={"procedure_tag": tag, "input_plate_tag": execution.input_plate_tag,
                   "output_plate_tag": execution.output_plate_tag, "user_tag": user_tag})

        for well in execution.input_wells:
            row_index, column_index = self._parse_position(well.position)
            self._driver.execute_query(
                "MATCH (e:ModularProcedureExecution {tag : $execution_tag}) "
                "MERGE (w:ExecutionWell {execution_tag : $execution_tag, position : $position, side : 'INPUT'}) "
                "SET w.row_index = $row_index, w.column_index = $column_index, "
                "w.output_positions = $output_positions "
                "MERGE (e)-[:HAS_WELL]->(w) "
                "WITH w "
                "MATCH (s:Sample) WHERE s.tag IN $sample_tags "
                "MERGE (s)-[:IN_WELL]->(w) ",
                routing_="w", execution_tag=execution_tag, position=well.position,
                row_index=row_index, column_index=column_index,
                output_positions=sorted(well.output_positions), sample_tags=sorted(well.sample_tags))

        for well in execution.output_wells:
            row_index, column_index = self._parse_position(well.position)
            self._driver.execute_query(
                "MATCH (e:ModularProcedureExecution {tag : $execution_tag}) "
                "MERGE (w:ExecutionWell {execution_tag : $execution_tag, position : $position, side : 'OUTPUT'}) "
                "SET w.row_index = $row_index, w.column_index = $column_index "
                "MERGE (e)-[:HAS_WELL]->(w) "
                "WITH w "
                "MATCH (s:Sample) WHERE s.tag IN $sample_tags "
                "MERGE (s)-[:IN_WELL]->(w) ",
                routing_="w", execution_tag=execution_tag, position=well.position,
                row_index=row_index, column_index=column_index,
                sample_tags=sorted(output_well_samples[well.position]))
            for ca_tag in well.condition_application_tags:
                self._driver.execute_query(
                    "MATCH (w:ExecutionWell {execution_tag : $execution_tag, position : $position, side : 'OUTPUT'}) "
                    "MATCH (c:ConditionApplication {tag : $ca_tag}) "
                    "MERGE (w)-[:HAS_APPLICATION]->(c) ",
                    routing_="w", execution_tag=execution_tag, position=well.position, ca_tag=ca_tag)

        done_submission_tags = self._driver.execute_query(
            "UNWIND $sample_tags as sample_tag "
            "MATCH (s:Sample {tag : sample_tag})<-[:HAS_SAMPLE]-(sub:Submission) "
            "MATCH (sub)-[r:IN_PROCEDURE]->(m:ModularProcedure {tag : $procedure_tag}) "
            "SET r.done = true, r.done_at = $done_at, r.done_by = $user_tag "
            "RETURN collect(DISTINCT sub.tag) as done_submissions",
            routing_="w", sample_tags=all_sample_tags, procedure_tag=tag, user_tag=user_tag,
            done_at=time.time(), result_transformer_=Result.value)
        done_submissions = done_submission_tags[0] if len(done_submission_tags) > 0 else []
        self._driver.execute_query(
            "MATCH (e:ModularProcedureExecution {tag : $execution_tag}) "
            "SET e.done_submission_tags = $done_submissions",
            routing_="w", execution_tag=execution_tag, done_submissions=done_submissions)

        return self.get_execution(execution_tag=execution_tag)

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
            "WITH w, collect(s.tag) as sample_tags "
            "RETURN {position: w.position, row_index: w.row_index, column_index: w.column_index, "
            "sample_tags: sample_tags, output_positions: w.output_positions} as well "
            "ORDER BY w.row_index, w.column_index",
            routing_="r", execution_tag=execution_tag, result_transformer_=Result.data)
        output_wells = self._driver.execute_query(
            "MATCH (e:ModularProcedureExecution {tag : $execution_tag})-[:HAS_WELL]->(w:ExecutionWell {side : 'OUTPUT'}) "
            "OPTIONAL MATCH (s:Sample)-[:IN_WELL]->(w) "
            "OPTIONAL MATCH (w)-[:HAS_APPLICATION]->(c:ConditionApplication) "
            "WITH w, collect(DISTINCT s.tag) as sample_tags, collect(DISTINCT c.tag) as ca_tags "
            "RETURN {position: w.position, row_index: w.row_index, column_index: w.column_index, "
            "sample_tags: sample_tags, condition_application_tags: ca_tags} as well "
            "ORDER BY w.row_index, w.column_index",
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
            "RETURN {tag: e.tag, procedure_tag: e.procedure_tag, input_plate_tag: e.input_plate_tag, "
            "output_plate_tag: e.output_plate_tag, user_tag: e.user_tag, created_at: e.created_at, "
            "done_submission_tags: e.done_submission_tags} as execution",
            routing_="r", execution_tag=execution_tag, result_transformer_=Result.data)
        execution = head[0]["execution"]
        execution["input_wells"] = [ProcedureExecutionInputWellModel(**well) for well in input_wells]
        execution["output_wells"] = [ProcedureExecutionOutputWellModel(**well) for well in output_wells]
        return ProcedureExecutionModel(**execution)

    def get_executions(self, tag: str) -> List[str]:
        "Returns the tags of the executions of the given procedure."
        if not self.exists(tag=tag):
            raise KeyError("Modular procedure not found.")
        return self._driver.execute_query(
            "MATCH (e:ModularProcedureExecution {procedure_tag : $tag}) "
            "RETURN e.tag as tag ORDER BY e.created_at ASC",
            routing_="r", tag=tag, result_transformer_=Result.value)

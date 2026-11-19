"""
Route-level tests for the modular procedure endpoints.
Uses FastAPI dependency_overrides with a fake database, like test_plate_runlist_routes.py.
"""

import sys
import time
from pathlib import Path

import pytest

SRC_DIR = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(SRC_DIR))

from config.enums.users.roles import UserRolesEnum
from config.models.user import UserModel
from config.models.procedures import (
    ModularProcedureBaseModel,
    ModularProcedureSubmissionModel,
    ProcedureExecutionModel,
    PublishModularProcedureModel,
)
from services.users import get_user_from_token
from lib.database.Database import get_db


def make_user(role=UserRolesEnum.STANDARD):
    return UserModel(
        tag="abcdefgh",
        firstname="Test",
        lastname="User",
        email="test.user@age.mpg.de",
        created_at=time.time(),
        role=role,
        allow_login=True,
    )


class FakeAttributesDB:
    "Minimal attributes stub: only what the procedure routes need (tree validation)."
    def get_parents(self, attribute_tag):
        return []


class FakeModularProceduresDB:
    def __init__(self):
        self.procedures = {
            "proc-1": ModularProcedureBaseModel(
                tag="proc-1", title="Protein Concentration Measurement", description="Measure it.",
                status="DRAFT", version=1, lineage_tag="proc-1", user_tag="abcdefgh", created_at=1.0,
                condition_application_tags=["ca-1"], protocol_tags=["protocol-1"]),
            "proc-2": ModularProcedureBaseModel(
                tag="proc-2", title="SP3 Digestion", description="Digest it.",
                status="PUBLISHED", version=1, lineage_tag="proc-2", content_hash="abc123", user_tag="abcdefgh",
                created_at=2.0, published_at=3.0,
                condition_application_tags=["ca-1"], protocol_tags=["protocol-2"],
                success_submission_state="PROCESSED"),
        }
        self.submission_links = {
            "proc-2": [
                ModularProcedureSubmissionModel(
                    procedure_tag="proc-2", submission_tag="subm-1", position=0,
                    created_at=10.0, done=False),
                ModularProcedureSubmissionModel(
                    procedure_tag="proc-2", submission_tag="subm-2", position=0,
                    created_at=11.0, done=False),
            ],
        }
        self.submission_procedures = {
            "subm-1": [
                ModularProcedureSubmissionModel(
                    procedure_tag="proc-2", submission_tag="subm-1", position=0,
                    created_at=10.0, done=False),
            ],
            "subm-2": [
                ModularProcedureSubmissionModel(
                    procedure_tag="proc-2", submission_tag="subm-2", position=0,
                    created_at=11.0, done=False),
            ],
        }
        self.sample_submissions = {"sample-1": "subm-1", "sample-2": "subm-1", "sample-3": "subm-2"}
        self.published = []
        self.linked = []
        self.done = []
        self.reopened = []
        self.unlinked = []
        self.finished = []
        self.set_states = []
        self.adopted_condition_applications = []
        self.state_history = {}
        self.executions = {}

    def exists(self, tag):
        return tag in self.procedures

    def get(self, tag):
        if tag not in self.procedures:
            raise KeyError("Modular procedure not found.")
        return self.procedures[tag]

    def find(self, search_string=None, status=None, limit=None, latest_only=False):
        tags = []
        for tag, procedure in self.procedures.items():
            if search_string is not None and search_string not in procedure.title:
                continue
            if status is not None and procedure.status != status:
                continue
            if latest_only:
                newer = [p for p in self.procedures.values()
                         if p.lineage_tag == procedure.lineage_tag and p.version > procedure.version
                         and (status is None or p.status == status)]
                if len(newer) > 0:
                    continue
            tags.append(tag)
        return tags

    def create_version(self, tag, user_tag):
        parent = self.get(tag)
        if parent.status != "PUBLISHED":
            raise ValueError("New versions can only be created from published modular procedures.")
        new_version = max([p.version for p in self.procedures.values()
                           if p.lineage_tag == parent.lineage_tag], default=parent.version) + 1
        new_tag = f"proc-v{new_version}"
        self.procedures[new_tag] = ModularProcedureBaseModel(
            tag=new_tag, title=parent.title, description=parent.description,
            status="DRAFT", version=new_version, lineage_tag=parent.lineage_tag,
            user_tag=user_tag, condition_application_tags=parent.condition_application_tags,
            protocol_tags=parent.protocol_tags)
        return self.procedures[new_tag]

    def get_versions(self, tag):
        procedure = self.get(tag)
        return [t for t, p in sorted(self.procedures.items(), key=lambda kv: kv[1].version)
                if p.lineage_tag == procedure.lineage_tag]

    def insert(self, title, description, user_tag, condition_application_tags=None,
               condition_application_trees=None, protocol_tags=None, plate_constraints=None,
               input_attribute_tags=None, output_attribute_tags=None, success_submission_state=None):
        condition_application_tags = list(condition_application_tags or [])
        for tree in (condition_application_trees or []):
            # simulate the condition application insert: hash-tagged, idempotent
            ca_tag = "ca-tree-" + tree.tag
            if ca_tag not in condition_application_tags:
                condition_application_tags.append(ca_tag)
        tag = "proc-new"
        if tag in self.procedures:
            raise ValueError("Tag is already in the database.")
        self.procedures[tag] = ModularProcedureBaseModel(
            tag=tag, title=title, description=description, status="DRAFT", version=1,
            user_tag=user_tag, condition_application_tags=condition_application_tags or [],
            protocol_tags=protocol_tags or [],
            input_plate_format=(plate_constraints or {}).get("input_plate_format"),
            input_plate_type=(plate_constraints or {}).get("input_plate_type"),
            output_plate_format=(plate_constraints or {}).get("output_plate_format"),
            output_plate_type=(plate_constraints or {}).get("output_plate_type"),
            input_attribute_tags=list(input_attribute_tags or []),
            output_attribute_tags=list(output_attribute_tags or []),
            success_submission_state=success_submission_state)
        return tag

    def update(self, tag, title, description, user_tag, condition_application_tags=None,
               condition_application_trees=None, protocol_tags=None, plate_constraints=None,
               input_attribute_tags=None, output_attribute_tags=None, success_submission_state=None):
        if tag not in self.procedures:
            raise ValueError("Modular procedure not found.")
        if self.procedures[tag].status == "PUBLISHED":
            raise ValueError("Published modular procedures are immutable.")
        self.procedures[tag].title = title
        self.procedures[tag].description = description
        return True

    def publish(self, tag, user_tag):
        if tag not in self.procedures:
            raise KeyError("Modular procedure not found.")
        if self.procedures[tag].status == "PUBLISHED":
            raise ValueError("Modular procedure is already published.")
        self.procedures[tag].status = "PUBLISHED"
        self.procedures[tag].content_hash = "deadbeef"
        self.published.append(tag)
        return PublishModularProcedureModel(tag=tag, version=1, content_hash="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")

    def link(self, tag, submission_tag, user_tag):
        if tag not in self.procedures:
            raise ValueError("Modular procedure not found.")
        if submission_tag in [link.submission_tag for link in self.submission_links.get(tag, [])]:
            raise ValueError("Submission is already linked to this modular procedure.")
        open_elsewhere = [link.procedure_tag for links in self.submission_procedures.values() for link in links
                          if link.submission_tag == submission_tag and link.procedure_tag != tag and not link.done]
        if len(open_elsewhere) > 0:
            raise ValueError(f"Submission is not done in another modular procedure yet: {', '.join(open_elsewhere)}. "
                             "A submission can only be linked to one modular procedure at a time.")
        self.linked.append((tag, submission_tag))
        return True

    def unlink(self, tag, submission_tag):
        self.unlinked.append((tag, submission_tag))
        return True

    def mark_done(self, tag, submission_tag, user_tag):
        self.done.append((tag, submission_tag, user_tag))
        self._set_link_done(tag, submission_tag, True)
        return True

    def reopen(self, tag, submission_tag):
        self.reopened.append((tag, submission_tag))
        self._set_link_done(tag, submission_tag, False)
        return True

    def _set_link_done(self, tag, submission_tag, done):
        for links in self.submission_procedures.values():
            for link in links:
                if link.procedure_tag == tag and link.submission_tag == submission_tag:
                    link.done = done
        for links in self.submission_links.values():
            for link in links:
                if link.procedure_tag == tag and link.submission_tag == submission_tag:
                    link.done = done

    def get_submissions(self, tag):
        if tag not in self.procedures:
            raise KeyError("Modular procedure not found.")
        return self.submission_links.get(tag, [])

    def get_submission_procedures(self, submission_tag):
        return self.submission_procedures.get(submission_tag, [])

    def execute(self, tag, execution, user_tag):
        # only running or succeeded executions occupy their output wells
        blocks = (lambda exec_model: exec_model.status == "RUNNING"
                  or getattr(exec_model, "wells_blocked", exec_model.status == "SUCCEEDED"))
        occupied = [well.position for exec_model in self.executions.values()
                    for well in exec_model.output_wells
                    if exec_model.output_plate_tag == execution.output_plate_tag
                    and blocks(exec_model)]
        conflicts = sorted(set(occupied) & {w.position for w in execution.output_wells})
        if len(conflicts) > 0:
            raise ValueError(f"Output wells already used by another execution: {', '.join(conflicts)}")
        if tag not in self.procedures:
            raise KeyError("Modular procedure not found.")
        if self.procedures[tag].status != "PUBLISHED":
            raise ValueError("Only published modular procedures can be executed.")
        if execution.input_plate_tag == "missing-plate" or execution.output_plate_tag == "missing-plate":
            raise ValueError("Plate not found.")
        input_positions = [well.position for well in execution.input_wells]
        output_positions = {well.position for well in execution.output_wells}
        if len(set(input_positions)) != len(input_positions):
            raise ValueError("Duplicate well positions are not allowed.")
        for well in execution.input_wells:
            if len(well.sample_tags) == 0:
                raise ValueError(f"Input well {well.position} has no samples.")
            for output_position in well.output_positions:
                if output_position not in output_positions:
                    raise ValueError(f"Output well {output_position} is not defined.")
        if "missing-sample" in [t for well in execution.input_wells for t in well.sample_tags]:
            raise ValueError("Samples not found: missing-sample")
        responsible_user_tag = execution.responsible_user_tag or user_tag
        if responsible_user_tag == "missing-user":
            raise ValueError("Responsible user not found: missing-user")
        all_metrics = list(execution.output_well_metrics) + list(execution.input_well_metrics or [])
        for metric in all_metrics:
            side_wells = execution.output_wells if metric.side == "OUTPUT" else execution.input_wells
            side_name = "output" if metric.side == "OUTPUT" else "input"
            if metric.position not in {w.position for w in side_wells}:
                raise ValueError(f"Metrics were given for a non-defined {side_name} well: {metric.position}")
            if metric.trait_tag not in ["trait-ugul", "trait-ph"]:
                raise ValueError(f"Traits not found: {metric.trait_tag}")
        input_sample_tags = [sample_tag for well in execution.input_wells for sample_tag in well.sample_tags]
        self.execution_counter = getattr(self, "execution_counter", 0) + 1
        execution_tag = f"exec-{self.execution_counter}"
        self.executions[execution_tag] = ProcedureExecutionModel(
            tag=execution_tag, procedure_tag=tag,
            input_plate_tag=execution.input_plate_tag, output_plate_tag=execution.output_plate_tag,
            user_tag=user_tag, responsible_user_tag=responsible_user_tag,
            created_at=4.0, status="RUNNING", done_submission_tags=[],
            input_well_metrics=[{"trait_tag": m.trait_tag, "attribute_tag": "att_concentration", "value": m.value}
                                for m in (execution.input_well_metrics or [])],
            input_wells=[{"position": w.position, "row_index": 0, "column_index": 0,
                          "sample_tags": w.sample_tags, "output_positions": w.output_positions,
                          "metrics": [{"trait_tag": m.trait_tag, "attribute_tag": "att_concentration", "value": m.value}
                                       for m in (execution.input_well_metrics or []) if m.position == w.position]}
                         for w in execution.input_wells],
            output_wells=[{"position": w.position, "row_index": 0, "column_index": 0,
                           "sample_tags": sorted({sample_tag for input_well in execution.input_wells
                                                   for sample_tag in input_well.sample_tags
                                                   if w.position in input_well.output_positions}),
                           "condition_application_tags": w.condition_application_tags,
                           "metrics": [{"trait_tag": m.trait_tag, "attribute_tag": "att_concentration", "value": m.value}
                                       for m in execution.output_well_metrics if m.position == w.position]}
                          for w in execution.output_wells])
        return self.executions[execution_tag]

    def finish_execution(self, execution_tag, outcome, user_tag, comment=None, block_output_wells=None):
        if execution_tag not in self.executions:
            raise KeyError("Procedure execution not found.")
        if outcome not in ("SUCCEEDED", "FAILED", "ABORTED"):
            raise ValueError("Outcome must be SUCCEEDED, FAILED or ABORTED.")
        execution = self.executions[execution_tag]
        if outcome == execution.status:
            raise ValueError(f"This procedure execution is already in state {execution.status}.")
        previous_state = execution.status
        input_sample_tags = [sample_tag for well in execution.input_wells for sample_tag in well.sample_tags]
        done_submissions = sorted({self.sample_submissions[sample_tag] for sample_tag in input_sample_tags
                                    if sample_tag in self.sample_submissions})
        if previous_state == "RUNNING":
            for submission_tag in done_submissions:
                self._set_link_done(execution.procedure_tag, submission_tag, True)
                self.finished.append((execution_tag, submission_tag, user_tag))
        if outcome == "SUCCEEDED":
            self.adopted_condition_applications.extend(
                (submission_tag, ca_tag)
                for submission_tag in done_submissions
                for ca_tag in self.procedures[execution.procedure_tag].condition_application_tags)
            self.set_states.extend((submission_tag, self.procedures[execution.procedure_tag].success_submission_state)
                                   for submission_tag in done_submissions
                                   if self.procedures[execution.procedure_tag].success_submission_state is not None)
        self.state_history.setdefault(execution_tag, []).append({"state": outcome, "created_at": 5.0, "user_tag": user_tag})
        execution.status = outcome
        execution.wells_blocked = block_output_wells if block_output_wells is not None else (outcome == "SUCCEEDED")
        execution.finished_at = 5.0
        execution.finished_by = user_tag
        execution.finish_comment = comment
        execution.done_submission_tags = done_submissions
        return execution

    def get_execution_states(self, execution_tag):
        if execution_tag not in self.executions:
            raise KeyError("Procedure execution not found.")
        history = self.state_history.get(execution_tag, []) + [{"state": "RUNNING", "created_at": 4.0, "user_tag": self.executions[execution_tag].user_tag}]
        return [{"state": entry["state"], "created_at": entry["created_at"], "user_tag": entry["user_tag"]}
                for entry in sorted(history, key=lambda entry: entry["created_at"], reverse=True)]

    def find_execution_tags(self, status=None, limit=None):
        tags = [tag for tag, execution in self.executions.items()
                if status is None or execution.status == status]
        tags.sort(key=lambda tag: self.executions[tag].created_at or 0, reverse=True)
        return tags if limit is None else tags[:limit]

    def find_execution_tags_by_submissions(self, submission_tags):
        submission_tags = set(submission_tags)
        tags = []
        for tag, execution in self.executions.items():
            sample_tags = {sample for well in execution.input_wells for sample in well.sample_tags} | \
                          {sample for well in execution.output_wells for sample in well.sample_tags}
            if any(self.sample_submissions.get(sample) in submission_tags for sample in sample_tags):
                tags.append(tag)
        return tags

    def get_sample_submission_map(self, sample_tags):
        return {sample_tag: [self.sample_submissions[sample_tag]]
                for sample_tag in sample_tags if sample_tag in self.sample_submissions}

    def get_submission_sample_locations(self, submission_tag):
        if submission_tag not in {"subm-1", "subm-2"}:
            raise KeyError("Submission not found.")
        sample_tags = [tag for tag, sub in self.sample_submissions.items() if sub == submission_tag]
        locations = []
        for sample_tag in sample_tags:
            entries = []
            for tag, execution in self.executions.items():
                for well in execution.input_wells:
                    if sample_tag in well.sample_tags:
                        entries.append({"procedure_tag": execution.procedure_tag, "execution_tag": tag,
                                         "status": execution.status or "RUNNING", "created_at": execution.created_at,
                                         "position": well.position, "side": "INPUT",
                                         "plate_tag": execution.input_plate_tag})
                for well in execution.output_wells:
                    if sample_tag in well.sample_tags:
                        entries.append({"procedure_tag": execution.procedure_tag, "execution_tag": tag,
                                         "status": execution.status or "RUNNING", "created_at": execution.created_at,
                                         "position": well.position, "side": "OUTPUT",
                                         "plate_tag": execution.output_plate_tag})
            if len(entries) == 0:
                continue
            latest_created_at = max(entry["created_at"] or 0 for entry in entries)
            latest = [entry for entry in entries if (entry["created_at"] or 0) == latest_created_at]
            head = latest[0]
            locations.append({"sample_tag": sample_tag, "procedure_tag": head["procedure_tag"],
                              "execution_tag": head["execution_tag"], "execution_status": head["status"],
                              "created_at": head["created_at"],
                              "wells": [{"plate_tag": entry["plate_tag"], "position": entry["position"], "side": entry["side"]}
                                        for entry in latest]})
        return locations

    def get_execution(self, execution_tag):
        if execution_tag not in self.executions:
            raise KeyError("Procedure execution not found.")
        return self.executions[execution_tag]

    def get_executions(self, tag):
        if tag not in self.procedures:
            raise KeyError("Modular procedure not found.")
        return [execution_tag for execution_tag, execution in self.executions.items()
                if execution.procedure_tag == tag]

    def set_execution_metrics(self, execution_tag, well_metrics, user_tag):
        if execution_tag not in self.executions:
            raise KeyError("Procedure execution not found.")
        execution = self.executions[execution_tag]
        metric_keys = [(m.position, m.trait_tag, m.side) for m in well_metrics]
        if len(set(metric_keys)) != len(metric_keys):
            raise ValueError("Duplicate metric positions are not allowed.")
        for metric in well_metrics:
            side_wells = execution.output_wells if metric.side == "OUTPUT" else execution.input_wells
            if metric.position not in {w.position for w in side_wells}:
                raise ValueError(f"Metrics were given for wells that are not {metric.side.lower()} wells of this execution: {metric.position}")
            if metric.trait_tag not in ["trait-ugul", "trait-ph"]:
                raise ValueError(f"Traits not found: {metric.trait_tag}")
        def _apply(wells, side):
            return [w.model_copy(update={"metrics":
                list(w.metrics) + [{"trait_tag": m.trait_tag, "attribute_tag": "att_concentration", "value": m.value}
                                   for m in well_metrics if m.position == w.position and m.side == side]})
                for w in wells]
        execution.output_wells = _apply(execution.output_wells, "OUTPUT")
        execution.input_wells = _apply(execution.input_wells, "INPUT")
        return execution


class FakeSubmissionsDB:
    def __init__(self, procedures):
        self._procedures = procedures
        self.scopes = {}

    def get_user_submission_scope_tags(self, user_tag):
        return self.scopes.get(user_tag)


class FakeDB:
    def __init__(self):
        self.modular_procedures = FakeModularProceduresDB()
        self.attributes = FakeAttributesDB()
        self.submissions = FakeSubmissionsDB(self.modular_procedures)


def _make_client(user, fake_db=None):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from routers.procedures.procedures import router as procedures_router

    app = FastAPI()
    app.include_router(procedures_router)
    fake_db = fake_db if fake_db is not None else FakeDB()
    app.dependency_overrides[get_db] = lambda: fake_db
    app.dependency_overrides[get_user_from_token] = lambda: user
    return TestClient(app)


@pytest.fixture
def client():
    "Curator client: modular procedure management is reserved for curators and admins."
    with _make_client(make_user(role=UserRolesEnum.CURATOR)) as c:
        yield c


class TestModularProcedureRoutes:
    def test_query_procedures(self, client):
        resp = client.get("/api/procedures/q")
        assert resp.status_code == 200
        assert set(resp.json()) == {"proc-1", "proc-2"}

    def test_query_procedures_by_status(self, client):
        resp = client.get("/api/procedures/q", params={"status": "PUBLISHED"})
        assert resp.status_code == 200
        assert resp.json() == ["proc-2"]

    def test_get_procedure(self, client):
        resp = client.get("/api/procedures/proc-1")
        assert resp.status_code == 200
        assert resp.json()["title"] == "Protein Concentration Measurement"
        assert resp.json()["status"] == "DRAFT"

    def test_get_missing_procedure_404(self, client):
        resp = client.get("/api/procedures/does-not-exist")
        assert resp.status_code == 404

    def test_insert_procedure(self, client):
        resp = client.post("/api/procedures/", json={
            "title": "New", "description": "New procedure",
            "condition_application_tags": ["ca-1"], "protocol_tags": ["protocol-1"]})
        assert resp.status_code == 200
        assert resp.json()["status"] == "DRAFT"

    def test_update_draft_procedure(self, client):
        resp = client.patch("/api/procedures/proc-1", json={
            "title": "Updated", "description": "Updated description"})
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated"

    def test_update_published_procedure_rejected(self, client):
        resp = client.patch("/api/procedures/proc-2", json={
            "title": "Updated", "description": "Nope"})
        assert resp.status_code == 400

    def test_publish_draft_procedure(self, client):
        resp = client.post("/api/procedures/proc-1/publish")
        assert resp.status_code == 200
        body = resp.json()
        assert body["tag"] == "proc-1"
        assert len(body["content_hash"]) == 64

    def test_publish_published_procedure_rejected(self, client):
        resp = client.post("/api/procedures/proc-2/publish")
        assert resp.status_code == 400

    def test_link_submission(self, client):
        # subm-1 is open in proc-2 -> rejected; after being done there -> allowed
        resp = client.post("/api/procedures/proc-1/link/subm-1")
        assert resp.status_code == 400
        client.post("/api/procedures/proc-2/link/subm-1/done")
        resp = client.post("/api/procedures/proc-1/link/subm-1")
        assert resp.status_code == 200
        assert resp.json() is True

    def test_get_procedure_submissions(self, client):
        resp = client.get("/api/procedures/proc-2/submissions")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 2
        assert body[0]["submission_tag"] == "subm-1"
        assert body[0]["created_at"] == 10.0
        assert body[0]["done"] is False

    def test_get_submission_procedures_ordered(self, client):
        resp = client.get("/api/procedures/submissions/subm-1")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 1
        assert body[0]["procedure_tag"] == "proc-2"
        assert body[0]["position"] == 0

    def test_mark_done(self, client):
        resp = client.post("/api/procedures/proc-2/link/subm-1/done")
        assert resp.status_code == 200
        assert resp.json() is True

    def test_reopen(self, client):
        resp = client.delete("/api/procedures/proc-2/link/subm-1/done")
        assert resp.status_code == 200
        assert resp.json() is True


class TestModularProcedurePermissions:
    def test_standard_user_rejected_on_insert(self):
        with _make_client(make_user(role=UserRolesEnum.STANDARD)) as c:
            resp = c.post("/api/procedures/", json={"title": "New", "description": "Nope"})
            assert resp.status_code == 403

    def test_standard_user_rejected_on_publish(self):
        with _make_client(make_user(role=UserRolesEnum.STANDARD)) as c:
            resp = c.post("/api/procedures/proc-1/publish")
            assert resp.status_code == 403

    def test_standard_user_rejected_on_link(self):
        with _make_client(make_user(role=UserRolesEnum.STANDARD)) as c:
            resp = c.post("/api/procedures/proc-1/link/subm-1")
            assert resp.status_code == 403

    def test_standard_user_rejected_on_mark_done(self):
        with _make_client(make_user(role=UserRolesEnum.STANDARD)) as c:
            resp = c.post("/api/procedures/proc-2/link/subm-1/done")
            assert resp.status_code == 403

    def test_admin_allowed_on_insert(self):
        with _make_client(make_user(role=UserRolesEnum.ADMIN)) as c:
            resp = c.post("/api/procedures/", json={"title": "New", "description": "Admin"})
            assert resp.status_code == 200

    def test_admin_allowed_on_mark_done(self):
        with _make_client(make_user(role=UserRolesEnum.ADMIN)) as c:
            resp = c.post("/api/procedures/proc-2/link/subm-1/done")
            assert resp.status_code == 200

class TestModularProcedureExecutionRoutes:
    def test_execute_published_procedure(self, client):
        resp = client.post("/api/procedures/proc-2/execute", json={
            "input_plate_tag": "plate-1", "output_plate_tag": "plate-2",
            "input_wells": [
                {"position": "A1", "sample_tags": ["sample-1", "sample-2"], "output_positions": ["A1"]},
                {"position": "B1", "sample_tags": ["sample-3"], "output_positions": ["A1", "B1", "C1"]},
            ],
            "output_wells": [
                {"position": "A1", "condition_application_tags": ["ca-heat"]},
                {"position": "B1", "condition_application_tags": []},
                {"position": "C1", "condition_application_tags": []},
            ]})
        assert resp.status_code == 200
        body = resp.json()
        assert body["tag"] == "exec-1"
        assert body["procedure_tag"] == "proc-2"
        # the execution starts RUNNING: the submissions are only freed on confirmation
        assert body["status"] == "RUNNING"
        assert body["done_submission_tags"] == []
        assert body["finished_at"] is None
        assert len(body["input_wells"]) == 2
        assert body["input_wells"][0]["sample_tags"] == ["sample-1", "sample-2"]
        assert body["input_wells"][1]["output_positions"] == ["A1", "B1", "C1"]
        assert len(body["output_wells"]) == 3
        assert body["output_wells"][0]["condition_application_tags"] == ["ca-heat"]

    def test_execute_draft_procedure_rejected(self, client):
        resp = client.post("/api/procedures/proc-1/execute", json={
            "input_plate_tag": "plate-1", "output_plate_tag": "plate-2", "input_wells": [], "output_wells": []})
        assert resp.status_code == 400

    def test_execute_with_missing_plate_rejected(self, client):
        resp = client.post("/api/procedures/proc-2/execute", json={
            "input_plate_tag": "missing-plate", "output_plate_tag": "plate-2", "input_wells": [], "output_wells": []})
        assert resp.status_code == 400

    def test_execute_with_undefined_output_well_rejected(self, client):
        resp = client.post("/api/procedures/proc-2/execute", json={
            "input_plate_tag": "plate-1", "output_plate_tag": "plate-2",
            "input_wells": [{"position": "A1", "sample_tags": ["sample-1"], "output_positions": ["Z9"]}],
            "output_wells": [{"position": "A1", "condition_application_tags": []}]})
        assert resp.status_code == 400

    def test_execute_with_empty_input_well_rejected(self, client):
        resp = client.post("/api/procedures/proc-2/execute", json={
            "input_plate_tag": "plate-1", "output_plate_tag": "plate-2",
            "input_wells": [{"position": "A1", "sample_tags": [], "output_positions": ["A1"]}],
            "output_wells": [{"position": "A1", "condition_application_tags": []}]})
        assert resp.status_code == 400

    def test_execute_with_missing_sample_rejected(self, client):
        resp = client.post("/api/procedures/proc-2/execute", json={
            "input_plate_tag": "plate-1", "output_plate_tag": "plate-2",
            "input_wells": [{"position": "A1", "sample_tags": ["missing-sample"], "output_positions": ["A1"]}],
            "output_wells": [{"position": "A1", "condition_application_tags": []}]})
        assert resp.status_code == 400

    def test_get_execution(self, client):
        client.post("/api/procedures/proc-2/execute", json={
            "input_plate_tag": "plate-1", "output_plate_tag": "plate-2",
            "input_wells": [{"position": "A1", "sample_tags": ["sample-1"], "output_positions": ["A1"]}],
            "output_wells": [{"position": "A1", "condition_application_tags": []}]})
        resp = client.get("/api/procedures/executions/exec-1")
        assert resp.status_code == 200
        assert resp.json()["procedure_tag"] == "proc-2"

    def test_get_missing_execution_404(self, client):
        resp = client.get("/api/procedures/executions/does-not-exist")
        assert resp.status_code == 404

    def test_get_executions_of_procedure(self, client):
        client.post("/api/procedures/proc-2/execute", json={
            "input_plate_tag": "plate-1", "output_plate_tag": "plate-2",
            "input_wells": [{"position": "A1", "sample_tags": ["sample-1"], "output_positions": ["A1"]}],
            "output_wells": [{"position": "A1", "condition_application_tags": []}]})
        resp = client.get("/api/procedures/proc-2/executions")
        assert resp.status_code == 200
        assert resp.json() == ["exec-1"]

    def test_standard_user_rejected_on_execute(self):
        with _make_client(make_user(role=UserRolesEnum.STANDARD)) as c:
            resp = c.post("/api/procedures/proc-2/execute", json={
                "input_plate_tag": "plate-1", "output_plate_tag": "plate-2",
                "input_wells": [], "output_wells": []})
            assert resp.status_code == 403

class TestModularProcedureVersionRoutes:
    def test_create_version_from_published(self, client):
        resp = client.post("/api/procedures/proc-2/versions")
        assert resp.status_code == 200
        body = resp.json()
        assert body["version"] == 2
        assert body["status"] == "DRAFT"
        assert body["lineage_tag"] == "proc-2"
        assert body["title"] == "SP3 Digestion"
        assert body["protocol_tags"] == ["protocol-2"]

    def test_create_version_from_draft_rejected(self, client):
        resp = client.post("/api/procedures/proc-1/versions")
        assert resp.status_code == 400

    def test_create_version_from_missing_404(self, client):
        resp = client.post("/api/procedures/does-not-exist/versions")
        assert resp.status_code == 404

    def test_get_versions(self, client):
        client.post("/api/procedures/proc-2/versions")
        resp = client.get("/api/procedures/proc-2/versions")
        assert resp.status_code == 200
        assert resp.json() == ["proc-2", "proc-v2"]

    def test_query_latest_only_returns_latest_published(self, client):
        client.post("/api/procedures/proc-2/versions")
        resp = client.get("/api/procedures/q", params={"status": "PUBLISHED", "latest_only": True})
        assert resp.status_code == 200
        assert resp.json() == ["proc-2"]

    def test_standard_user_rejected_on_create_version(self):
        with _make_client(make_user(role=UserRolesEnum.STANDARD)) as c:
            resp = c.post("/api/procedures/proc-2/versions")
            assert resp.status_code == 403


class TestModularProcedureExecutionOccupancy:
    def test_output_well_occupied_by_other_execution_rejected(self, client):
        first = client.post("/api/procedures/proc-2/execute", json={
            "input_plate_tag": "plate-1", "output_plate_tag": "plate-2",
            "input_wells": [{"position": "A1", "sample_tags": ["sample-1"], "output_positions": ["A1"]}],
            "output_wells": [{"position": "A1", "condition_application_tags": []}]})
        assert first.status_code == 200
        second = client.post("/api/procedures/proc-2/execute", json={
            "input_plate_tag": "plate-1", "output_plate_tag": "plate-2",
            "input_wells": [{"position": "B1", "sample_tags": ["sample-2"], "output_positions": ["A1"]}],
            "output_wells": [{"position": "A1", "condition_application_tags": []}]})
        assert second.status_code == 400
        assert "already used" in second.json()["detail"]

    def test_output_well_on_other_plate_allowed(self, client):
        first = client.post("/api/procedures/proc-2/execute", json={
            "input_plate_tag": "plate-1", "output_plate_tag": "plate-2",
            "input_wells": [{"position": "A1", "sample_tags": ["sample-1"], "output_positions": ["A1"]}],
            "output_wells": [{"position": "A1", "condition_application_tags": []}]})
        assert first.status_code == 200
        second = client.post("/api/procedures/proc-2/execute", json={
            "input_plate_tag": "plate-1", "output_plate_tag": "plate-3",
            "input_wells": [{"position": "B1", "sample_tags": ["sample-2"], "output_positions": ["A1"]}],
            "output_wells": [{"position": "A1", "condition_application_tags": []}]})
        assert second.status_code == 200

class TestModularProcedureExecutionMetricsRoutes:
    def test_execute_with_responsible_user_and_metrics(self, client):
        resp = client.post("/api/procedures/proc-2/execute", json={
            "input_plate_tag": "plate-1", "output_plate_tag": "plate-2",
            "responsible_user_tag": "ijklmnop",
            "input_wells": [{"position": "A1", "sample_tags": ["sample-1"], "output_positions": ["A1"]}],
            "output_wells": [{"position": "A1", "condition_application_tags": []}],
            "output_well_metrics": [{"position": "A1", "trait_tag": "trait-ugul", "value": 2.5}]})
        assert resp.status_code == 200
        body = resp.json()
        assert body["responsible_user_tag"] == "ijklmnop"
        assert body["output_wells"][0]["metrics"] == [{"trait_tag": "trait-ugul", "attribute_tag": "att_concentration", "value": 2.5}]

    def test_execute_responsible_user_defaults_to_executing_user(self, client):
        resp = client.post("/api/procedures/proc-2/execute", json={
            "input_plate_tag": "plate-1", "output_plate_tag": "plate-2",
            "input_wells": [{"position": "A1", "sample_tags": ["sample-1"], "output_positions": ["A1"]}],
            "output_wells": [{"position": "A1", "condition_application_tags": []}]})
        assert resp.status_code == 200
        assert resp.json()["responsible_user_tag"] == "abcdefgh"

    def test_execute_with_missing_responsible_user_rejected(self, client):
        resp = client.post("/api/procedures/proc-2/execute", json={
            "input_plate_tag": "plate-1", "output_plate_tag": "plate-2",
            "responsible_user_tag": "missing-user",
            "input_wells": [{"position": "A1", "sample_tags": ["sample-1"], "output_positions": ["A1"]}],
            "output_wells": [{"position": "A1", "condition_application_tags": []}]})
        assert resp.status_code == 400

    def test_execute_with_metrics_for_undefined_well_rejected(self, client):
        resp = client.post("/api/procedures/proc-2/execute", json={
            "input_plate_tag": "plate-1", "output_plate_tag": "plate-2",
            "input_wells": [{"position": "A1", "sample_tags": ["sample-1"], "output_positions": ["A1"]}],
            "output_wells": [{"position": "A1", "condition_application_tags": []}],
            "output_well_metrics": [{"position": "Z9", "trait_tag": "trait-ugul", "value": 1.0}]})
        assert resp.status_code == 400

    def test_set_metrics_after_execution(self, client):
        client.post("/api/procedures/proc-2/execute", json={
            "input_plate_tag": "plate-1", "output_plate_tag": "plate-2",
            "input_wells": [{"position": "A1", "sample_tags": ["sample-1"], "output_positions": ["A1"]}],
            "output_wells": [{"position": "A1", "condition_application_tags": []}]})
        resp = client.post("/api/procedures/executions/exec-1/metrics",
            json=[{"position": "A1", "trait_tag": "trait-ugul", "value": 3.1}])
        assert resp.status_code == 200
        assert resp.json()["output_wells"][0]["metrics"][-1] == {"trait_tag": "trait-ugul", "attribute_tag": "att_concentration", "value": 3.1}

    def test_set_metrics_for_non_output_well_rejected(self, client):
        client.post("/api/procedures/proc-2/execute", json={
            "input_plate_tag": "plate-1", "output_plate_tag": "plate-2",
            "input_wells": [{"position": "A1", "sample_tags": ["sample-1"], "output_positions": ["A1"]}],
            "output_wells": [{"position": "A1", "condition_application_tags": []}]})
        resp = client.post("/api/procedures/executions/exec-1/metrics",
            json=[{"position": "B1", "trait_tag": "trait-ugul", "value": 3.1}])
        assert resp.status_code == 400

    def test_set_metrics_on_missing_execution_404(self, client):
        resp = client.post("/api/procedures/executions/does-not-exist/metrics",
            json=[{"position": "A1", "trait_tag": "trait-ugul", "value": 3.1}])
        assert resp.status_code == 404

    def test_standard_user_rejected_on_set_metrics(self):
        with _make_client(make_user(role=UserRolesEnum.STANDARD)) as c:
            resp = c.post("/api/procedures/executions/exec-1/metrics",
                json=[{"position": "A1", "trait_tag": "trait-ugul", "value": 3.1}])
            assert resp.status_code == 403

    def test_execute_with_unknown_trait_rejected(self, client):
        resp = client.post("/api/procedures/proc-2/execute", json={
            "input_plate_tag": "plate-1", "output_plate_tag": "plate-2",
            "input_wells": [{"position": "A1", "sample_tags": ["sample-1"], "output_positions": ["A1"]}],
            "output_wells": [{"position": "A1", "condition_application_tags": []}],
            "output_well_metrics": [{"position": "A1", "trait_tag": "missing-trait", "value": 1.0}]})
        assert resp.status_code == 400
        assert "Traits not found" in resp.json()["detail"]

class TestModularProcedureMultipleSubmissions:
    def test_multiple_submissions_linked_to_one_procedure(self, client):
        resp = client.get("/api/procedures/proc-2/submissions")
        assert resp.status_code == 200
        assert [link["submission_tag"] for link in resp.json()] == ["subm-1", "subm-2"]

    def test_execute_with_samples_from_multiple_submissions(self, client):
        resp = client.post("/api/procedures/proc-2/execute", json={
            "input_plate_tag": "plate-1", "output_plate_tag": "plate-2",
            "input_wells": [
                {"position": "A1", "sample_tags": ["sample-1", "sample-2"], "output_positions": ["A1"]},
                {"position": "B1", "sample_tags": ["sample-3"], "output_positions": ["A1"]},
            ],
            "output_wells": [{"position": "A1", "condition_application_tags": []}]})
        assert resp.status_code == 200
        body = resp.json()
        # both submissions own samples on the input plate -> both are freed once the execution is confirmed
        assert body["done_submission_tags"] == []
        resp = client.post("/api/procedures/executions/exec-1/finish", json={"outcome": "SUCCEEDED"})
        assert resp.status_code == 200
        assert resp.json()["done_submission_tags"] == ["subm-1", "subm-2"]
        assert resp.json()["status"] == "SUCCEEDED"

    def test_execute_marks_only_submissions_with_input_samples_done(self, client):
        resp = client.post("/api/procedures/proc-2/execute", json={
            "input_plate_tag": "plate-1", "output_plate_tag": "plate-2",
            "input_wells": [
                {"position": "A1", "sample_tags": ["sample-1"], "output_positions": ["A1"]},
            ],
            "output_wells": [{"position": "A1", "condition_application_tags": []}]})
        assert resp.status_code == 200
        assert resp.json()["done_submission_tags"] == []
        resp = client.post("/api/procedures/executions/exec-1/finish", json={"outcome": "ABORTED"})
        assert resp.status_code == 200
        assert resp.json()["done_submission_tags"] == ["subm-1"]
        assert resp.json()["status"] == "ABORTED"

class TestModularProcedureExecutionFinishRoutes:
    def _execute(self, client):
        resp = client.post("/api/procedures/proc-2/execute", json={
            "input_plate_tag": "plate-1", "output_plate_tag": "plate-2",
            "input_wells": [{"position": "A1", "sample_tags": ["sample-1"], "output_positions": ["A1"]}],
            "output_wells": [{"position": "A1", "condition_application_tags": []}]})
        assert resp.status_code == 200
        assert resp.json()["status"] == "RUNNING"

    def _db(self, client):
        return client.app.dependency_overrides[get_db]().modular_procedures

    def test_finish_success_frees_submissions_and_adopts_condition_applications(self, client):
        self._execute(client)
        resp = client.post("/api/procedures/executions/exec-1/finish", json={"outcome": "SUCCEEDED"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "SUCCEEDED"
        assert body["finished_by"] == "abcdefgh"
        assert body["done_submission_tags"] == ["subm-1"]
        db = self._db(client)
        assert ("subm-1", "ca-1") in db.adopted_condition_applications
        assert ("subm-1", "PROCESSED") in db.set_states

    def test_finish_failed_frees_submissions_but_adopts_nothing(self, client):
        self._execute(client)
        resp = client.post("/api/procedures/executions/exec-1/finish", json={"outcome": "FAILED", "comment": "robot error"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "FAILED"
        assert body["finish_comment"] == "robot error"
        assert body["done_submission_tags"] == ["subm-1"]
        db = self._db(client)
        assert db.set_states == []
        assert db.adopted_condition_applications == []

    def test_finish_frees_submission_for_next_module(self, client):
        self._execute(client)
        resp = client.post("/api/procedures/proc-1/link/subm-1")
        assert resp.status_code == 400
        client.post("/api/procedures/executions/exec-1/finish", json={"outcome": "SUCCEEDED"})
        resp = client.post("/api/procedures/proc-1/link/subm-1")
        assert resp.status_code == 200

    def test_finish_twice_rejected(self, client):
        self._execute(client)
        client.post("/api/procedures/executions/exec-1/finish", json={"outcome": "SUCCEEDED"})
        resp = client.post("/api/procedures/executions/exec-1/finish", json={"outcome": "SUCCEEDED"})
        assert resp.status_code == 400
        assert "already in state" in resp.json()["detail"]

    def test_state_change_correction_allowed(self, client):
        self._execute(client)
        resp = client.post("/api/procedures/executions/exec-1/finish", json={"outcome": "FAILED"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "FAILED"
        resp = client.post("/api/procedures/executions/exec-1/finish", json={"outcome": "SUCCEEDED"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "SUCCEEDED"

    def test_execution_states_history(self, client):
        self._execute(client)
        client.post("/api/procedures/executions/exec-1/finish", json={"outcome": "SUCCEEDED"})
        resp = client.get("/api/procedures/executions/exec-1/states")
        assert resp.status_code == 200
        body = resp.json()
        assert [entry["state"] for entry in body] == ["SUCCEEDED", "RUNNING"]
        assert body[0]["user_tag"] == "abcdefgh"
        assert body[1]["user_tag"] == "abcdefgh"

    def test_execution_states_missing_execution_404(self, client):
        resp = client.get("/api/procedures/executions/does-not-exist/states")
        assert resp.status_code == 404

    def test_finish_invalid_outcome_rejected(self, client):
        self._execute(client)
        resp = client.post("/api/procedures/executions/exec-1/finish", json={"outcome": "RUNNING"})
        assert resp.status_code == 422

    def test_finish_missing_execution_404(self, client):
        resp = client.post("/api/procedures/executions/does-not-exist/finish", json={"outcome": "SUCCEEDED"})
        assert resp.status_code == 404

    def test_standard_user_rejected_on_finish(self):
        with _make_client(make_user(role=UserRolesEnum.STANDARD)) as c:
            resp = c.post("/api/procedures/executions/exec-1/finish", json={"outcome": "SUCCEEDED"})
            assert resp.status_code == 403

    def test_execute_with_input_well_metrics(self, client):
        resp = client.post("/api/procedures/proc-2/execute", json={
            "input_plate_tag": "plate-1", "output_plate_tag": "plate-2",
            "input_wells": [{"position": "A1", "sample_tags": ["sample-1"], "output_positions": ["A1"]}],
            "output_wells": [{"position": "A1", "condition_application_tags": []}],
            "input_well_metrics": [{"position": "A1", "trait_tag": "trait-ugul", "value": 1.5, "side": "INPUT"}]})
        assert resp.status_code == 200
        body = resp.json()
        assert body["input_wells"][0]["metrics"] == [{"trait_tag": "trait-ugul", "attribute_tag": "att_concentration", "value": 1.5}]
        assert body["input_well_metrics"] == [{"trait_tag": "trait-ugul", "attribute_tag": "att_concentration", "value": 1.5}]


class TestModularProcedureExecutionOverviewRoutes:
    def _execute_two_submissions(self, client, tag="exec-1"):
        resp = client.post("/api/procedures/proc-2/execute", json={
            "input_plate_tag": "plate-1", "output_plate_tag": "plate-2",
            "input_wells": [
                {"position": "A1", "sample_tags": ["sample-1"], "output_positions": ["A1"]},
                {"position": "B1", "sample_tags": ["sample-3"], "output_positions": ["B1"]},
            ],
            "output_wells": [
                {"position": "A1", "condition_application_tags": ["ca-heat"]},
                {"position": "B1", "condition_application_tags": []},
            ],
            "output_well_metrics": [{"position": "A1", "trait_tag": "trait-ugul", "value": 2.5}],
            "input_well_metrics": [{"position": "A1", "trait_tag": "trait-ugul", "value": 1.0, "side": "INPUT"}]})
        assert resp.status_code == 200
        assert resp.json()["tag"] == tag

    def _shared_db(self, client):
        return client.app.dependency_overrides[get_db]()

    def _scoped_client(self, shared_db, scope):
        user = make_user(role=UserRolesEnum.STANDARD)
        client = _make_client(user, fake_db=shared_db)
        shared_db.submissions.scopes[user.tag] = scope
        return client

    def test_curator_sees_all_executions(self, client):
        shared_db = self._shared_db(client)
        self._execute_two_submissions(client)
        client.post("/api/procedures/proc-2/execute", json={
            "input_plate_tag": "plate-1", "output_plate_tag": "plate-3",
            "input_wells": [{"position": "D1", "sample_tags": ["sample-2"], "output_positions": ["D1"]}],
            "output_wells": [{"position": "D1", "condition_application_tags": []}]})
        resp = client.get("/api/procedures/executions/q")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 2
        by_tag = {summary["tag"]: summary for summary in body}
        assert by_tag["exec-1"]["n_input_wells"] == 2
        assert by_tag["exec-2"]["n_input_wells"] == 1
        assert by_tag["exec-1"]["status"] == "RUNNING"

    def test_standard_user_sees_only_own_submission_executions(self, client):
        shared_db = self._shared_db(client)
        self._execute_two_submissions(client)
        client.post("/api/procedures/proc-2/execute", json={
            "input_plate_tag": "plate-1", "output_plate_tag": "plate-3",
            "input_wells": [{"position": "D1", "sample_tags": ["sample-3"], "output_positions": ["D1"]}],
            "output_wells": [{"position": "D1", "condition_application_tags": []}]})
        scoped = self._scoped_client(shared_db, ["subm-1"])
        resp = scoped.get("/api/procedures/executions/q")
        assert resp.status_code == 200
        body = resp.json()
        assert [summary["tag"] for summary in body] == ["exec-1"]

    def test_standard_user_details_are_masked(self, client):
        shared_db = self._shared_db(client)
        self._execute_two_submissions(client)
        scoped = self._scoped_client(shared_db, ["subm-1"])
        resp = scoped.get("/api/procedures/executions/exec-1")
        assert resp.status_code == 200
        body = resp.json()
        assert [well["position"] for well in body["input_wells"]] == ["A1"]
        assert [well["position"] for well in body["output_wells"]] == ["A1"]
        assert body["input_wells"][0]["sample_tags"] == ["sample-1"]
        assert body["input_wells"][0]["metrics"] == [{"trait_tag": "trait-ugul", "attribute_tag": "att_concentration", "value": 1.0}]
        assert body["input_well_metrics"] == []

    def test_standard_user_shared_well_hides_foreign_values(self, client):
        shared_db = self._shared_db(client)
        resp = client.post("/api/procedures/proc-2/execute", json={
            "input_plate_tag": "plate-1", "output_plate_tag": "plate-2",
            "input_wells": [{"position": "A1", "sample_tags": ["sample-1", "sample-3"], "output_positions": ["A1"]}],
            "output_wells": [{"position": "A1", "condition_application_tags": ["ca-heat"]}],
            "output_well_metrics": [{"position": "A1", "trait_tag": "trait-ugul", "value": 2.5}],
            "input_well_metrics": [{"position": "A1", "trait_tag": "trait-ugul", "value": 1.0, "side": "INPUT"}]})
        assert resp.status_code == 200
        scoped = self._scoped_client(shared_db, ["subm-1"])
        body = scoped.get("/api/procedures/executions/exec-1").json()
        assert body["input_wells"][0]["sample_tags"] == ["sample-1"]
        assert body["input_wells"][0]["metrics"] == []
        assert body["output_wells"][0]["metrics"] == []
        assert body["output_wells"][0]["condition_application_tags"] == []
        assert body["input_well_metrics"] == []


class TestModularProcedureExecutionRerunAndLocations:
    def _execute(self, client, sample="sample-1", input_position="A1", output_position="A1"):
        resp = client.post("/api/procedures/proc-2/execute", json={
            "input_plate_tag": "plate-1", "output_plate_tag": "plate-2",
            "input_wells": [{"position": input_position, "sample_tags": [sample], "output_positions": [output_position]}],
            "output_wells": [{"position": output_position, "condition_application_tags": []}]})
        assert resp.status_code == 200
        return resp.json()["tag"]

    def test_output_wells_free_after_abort(self, client):
        first = self._execute(client)
        resp = client.post(f"/api/procedures/executions/{first}/finish", json={"outcome": "ABORTED"})
        assert resp.json()["wells_blocked"] is False
        # the same wells can be used again: the aborted run does not block them
        second = self._execute(client)
        assert second != first

    def test_output_wells_stay_blocked_if_selected_on_abort(self, client):
        """An aborted liquid handler run leaves the pipetted wells dirty: the user can
        keep them blocked so they are never re-used."""
        first = self._execute(client)
        resp = client.post(f"/api/procedures/executions/{first}/finish",
            json={"outcome": "ABORTED", "block_output_wells": True})
        assert resp.json()["wells_blocked"] is True
        second = client.post("/api/procedures/proc-2/execute", json={
            "input_plate_tag": "plate-1", "output_plate_tag": "plate-2",
            "input_wells": [{"position": "B1", "sample_tags": ["sample-2"], "output_positions": ["A1"]}],
            "output_wells": [{"position": "A1", "condition_application_tags": []}]})
        assert second.status_code == 400
        assert "already used" in second.json()["detail"]

    def test_output_wells_can_be_unblocked_on_success(self, client):
        first = self._execute(client)
        resp = client.post(f"/api/procedures/executions/{first}/finish",
            json={"outcome": "SUCCEEDED", "block_output_wells": False})
        assert resp.json()["wells_blocked"] is False
        second = self._execute(client)
        assert second != first

    def test_output_wells_blocked_while_running(self, client):
        self._execute(client)
        resp = client.post("/api/procedures/proc-2/execute", json={
            "input_plate_tag": "plate-1", "output_plate_tag": "plate-2",
            "input_wells": [{"position": "B1", "sample_tags": ["sample-2"], "output_positions": ["A1"]}],
            "output_wells": [{"position": "A1", "condition_application_tags": []}]})
        assert resp.status_code == 400
        assert "already used" in resp.json()["detail"]

    def test_submission_sample_locations(self, client):
        self._execute(client)
        resp = client.get("/api/procedures/submissions/subm-1/wells")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 1
        location = body[0]
        assert location["sample_tag"] == "sample-1"
        assert location["execution_status"] == "RUNNING"
        assert {well["side"] for well in location["wells"]} == {"INPUT", "OUTPUT"}
        input_well = [well for well in location["wells"] if well["side"] == "INPUT"][0]
        assert input_well["plate_tag"] == "plate-1" and input_well["position"] == "A1"
        output_well = [well for well in location["wells"] if well["side"] == "OUTPUT"][0]
        assert output_well["plate_tag"] == "plate-2" and output_well["position"] == "A1"

    def test_submission_sample_locations_hidden_for_restricted_users(self, client):
        shared_db = client.app.dependency_overrides[get_db]()
        self._execute(client)
        user = make_user(role=UserRolesEnum.STANDARD)
        with _make_client(user, fake_db=shared_db) as scoped:
            shared_db.submissions.scopes[user.tag] = ["subm-2"]
            resp = scoped.get("/api/procedures/submissions/subm-1/wells")
            assert resp.status_code == 404
        resp = client.get("/api/procedures/submissions/does-not-exist/wells")
        assert resp.status_code == 404


class TestSingleOpenModuleConstraint:
    def test_link_submission_with_open_link_elsewhere_rejected(self, client):
        # subm-2 is linked to proc-2 and not done there -> must not be linkable to proc-1
        resp = client.post("/api/procedures/proc-1/link/subm-2")
        assert resp.status_code == 400
        assert "one modular procedure at a time" in resp.json()["detail"]

    def test_link_submission_after_done_allowed(self, client):
        # subm-1 is linked to proc-2; mark it done there -> it can proceed to the next module
        resp = client.post("/api/procedures/proc-2/link/subm-1/done")
        assert resp.status_code == 200
        resp = client.post("/api/procedures/proc-1/link/subm-1")
        assert resp.status_code == 200

    def test_reopen_makes_link_block_again(self, client):
        client.post("/api/procedures/proc-2/link/subm-1/done")
        client.post("/api/procedures/proc-1/link/subm-1")
        client.delete("/api/procedures/proc-2/link/subm-1/done")
        resp = client.post("/api/procedures/proc-1/link/subm-1")
        assert resp.status_code == 400

class TestModularProcedureConditionApplicationTrees:
    def test_insert_with_new_condition_application_tree(self, client):
        resp = client.post("/api/procedures/", json={
            "title": "Liquid Handling", "description": "Define it newly.",
            "condition_application_trees": [
                {"tag": "att_liquid_handler", "type": "attribute", "children": [
                    {"tag": "att_liquid_handler:hamilton", "type": "trait", "children": []}
                ]}
            ]})
        assert resp.status_code == 200
        body = resp.json()
        assert body["tag"] == "proc-new"
        assert body["condition_application_tags"] == ["ca-tree-att_liquid_handler"]

    def test_insert_reuses_existing_ca_tags_and_trees_together(self, client):
        resp = client.post("/api/procedures/", json={
            "title": "Mixed", "description": "Reuse and define.",
            "condition_application_tags": ["ca-1"],
            "condition_application_trees": [
                {"tag": "att_liquid_handler", "type": "attribute", "children": [
                    {"tag": "att_liquid_handler:hamilton", "type": "trait", "children": []}
                ]}
            ]})
        assert resp.status_code == 200
        assert sorted(resp.json()["condition_application_tags"]) == ["ca-1", "ca-tree-att_liquid_handler"]

    def test_insert_with_nested_tree(self, client):
        # attribute -> trait -> child attribute -> trait with value (like a submission insert)
        resp = client.post("/api/procedures/", json={
            "title": "Nested", "description": "Nested tree.",
            "condition_application_trees": [
                {"tag": "att_compound", "type": "attribute", "children": [
                    {"tag": "att_compound:dmso", "type": "trait", "children": [
                        {"tag": "att_concentration", "type": "attribute", "children": [
                            {"tag": "mM", "type": "trait", "value": 2, "children": []}
                        ]}
                    ]}
                ]}
            ]})
        assert resp.status_code == 200
        assert resp.json()["condition_application_tags"] == ["ca-tree-att_compound"]

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
    SUBMISSION_STATE_CHOICES,
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


def _split_ref(ref, primary):
    "Splits a well reference into (plate, position): plain positions belong to the primary plate."
    if isinstance(ref, str) and ":" in ref:
        plate_tag, position = ref.split(":", 1)
        return plate_tag, position
    return primary, ref


def _design_plates(design, side):
    primary = getattr(design, f"{side}_plate_tag")
    additional = list(getattr(design, f"additional_{side}_plate_tags", None) or [])
    ordered, seen = [], set()
    for plate_tag in ([primary] if primary else []) + additional:
        if plate_tag not in seen:
            seen.add(plate_tag)
            ordered.append(plate_tag)
    return ordered


def _well_plate(well, primary):
    return getattr(well, "plate_tag", None) or primary


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

    def retire(self, tag, user_tag):
        if tag not in self.procedures:
            raise KeyError("Modular procedure not found.")
        procedure = self.procedures[tag]
        if procedure.status == "RETIRED":
            raise ValueError("This modular procedure is already retired.")
        if procedure.status != "PUBLISHED":
            raise ValueError("Only published modular procedures can be retired.")
        self.procedures[tag] = procedure.model_copy(update={"status": "RETIRED"})
        return self.procedures[tag]

    def get_versions(self, tag):
        procedure = self.get(tag)
        return [t for t, p in sorted(self.procedures.items(), key=lambda kv: kv[1].version)
                if p.lineage_tag == procedure.lineage_tag]

    def insert(self, title, description, user_tag, condition_application_tags=None,
               condition_application_trees=None, protocol_tags=None, plate_constraints=None,
               input_attribute_tags=None, output_attribute_tags=None, success_submission_state=None,
               required_submission_state=None,
               pubmed_ids=None, min_output_wells_per_sample=1, max_output_wells_per_sample=None):
        self._validate_sample_multiplicity(min_output_wells_per_sample, max_output_wells_per_sample)
        self._validate_submission_state(required_submission_state)
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
            success_submission_state=success_submission_state,
            required_submission_state=required_submission_state,
            pubmed_ids=list(pubmed_ids or []),
            min_output_wells_per_sample=min_output_wells_per_sample if min_output_wells_per_sample is not None else 1,
            max_output_wells_per_sample=max_output_wells_per_sample)
        return tag

    @staticmethod
    def _validate_submission_state(required_submission_state):
        if required_submission_state is None:
            return
        if required_submission_state not in SUBMISSION_STATE_CHOICES:
            raise ValueError(f"Unknown submission state: {required_submission_state}")

    @staticmethod
    def _validate_sample_multiplicity(min_output_wells_per_sample, max_output_wells_per_sample):
        if min_output_wells_per_sample is None:
            min_output_wells_per_sample = 1
        if not isinstance(min_output_wells_per_sample, int) or min_output_wells_per_sample < 1:
            raise ValueError("min_output_wells_per_sample must be an integer >= 1.")
        if max_output_wells_per_sample is not None and (
                not isinstance(max_output_wells_per_sample, int)
                or max_output_wells_per_sample < min_output_wells_per_sample):
            raise ValueError("max_output_wells_per_sample must be an integer >= min_output_wells_per_sample or None.")

    def update(self, tag, title, description, user_tag, condition_application_tags=None,
               condition_application_trees=None, protocol_tags=None, plate_constraints=None,
               input_attribute_tags=None, output_attribute_tags=None, success_submission_state=None,
               required_submission_state=None,
               pubmed_ids=None, min_output_wells_per_sample=1, max_output_wells_per_sample=None):
        if tag not in self.procedures:
            raise ValueError("Modular procedure not found.")
        if self.procedures[tag].status == "PUBLISHED":
            raise ValueError("Published modular procedures are immutable.")
        self._validate_sample_multiplicity(min_output_wells_per_sample, max_output_wells_per_sample)
        self.procedures[tag].title = title
        self.procedures[tag].description = description
        self.procedures[tag].pubmed_ids = list(pubmed_ids or [])
        self._validate_submission_state(required_submission_state)
        self.procedures[tag].success_submission_state = success_submission_state
        self.procedures[tag].required_submission_state = required_submission_state
        self.procedures[tag].min_output_wells_per_sample = min_output_wells_per_sample if min_output_wells_per_sample is not None else 1
        self.procedures[tag].max_output_wells_per_sample = max_output_wells_per_sample
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
        if self.procedures[tag].status == "RETIRED":
            raise ValueError("This modular procedure is retired and can no longer be assigned to submissions.")
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
        input_plates = _design_plates(execution, "input")
        output_plates = _design_plates(execution, "output")
        output_keys = {(_well_plate(w, output_plates[0]), w.position) for w in execution.output_wells}
        if any(plate == "missing-plate" for plate in input_plates + output_plates):
            raise ValueError("Plate not found.")
        def _exec_output_plates(exec_model):
            tags = list(getattr(exec_model, "output_plate_tags", None) or [])
            return tags if len(tags) > 0 else ([exec_model.output_plate_tag] if exec_model.output_plate_tag else [])
        occupied = [(_well_plate(w, ps[0]), w.position)
                    for exec_model in self.executions.values()
                    for ps in [_exec_output_plates(exec_model)] for w in exec_model.output_wells
                    if ps[0] in output_plates and blocks(exec_model)]
        conflicts = sorted({f"{plate}:{pos}" for plate, pos in (set(occupied) & output_keys)})
        if len(conflicts) > 0:
            raise ValueError(f"Output wells on {conflicts[0].split(':')[0]} already used by another execution: "
                             f"{', '.join(sorted({c.split(':')[1] for c in conflicts}))}")
        if tag not in self.procedures:
            raise KeyError("Modular procedure not found.")
        if self.procedures[tag].status != "PUBLISHED":
            raise ValueError("Only published modular procedures can be executed.")
        if execution.input_plate_tag == "missing-plate" or execution.output_plate_tag == "missing-plate":
            raise ValueError("Plate not found.")
        if any(t == "missing-plate" for t in _design_plates(execution, "input") + _design_plates(execution, "output")):
            raise ValueError("Plate not found.")
        input_keys = [(_well_plate(w, input_plates[0]), w.position) for w in execution.input_wells]
        output_key_set = {(_well_plate(w, output_plates[0]), w.position) for w in execution.output_wells}
        if len(set(input_keys)) != len(input_keys) or len(output_key_set) != len(execution.output_wells):
            raise ValueError("Duplicate well positions are not allowed.")
        for well in execution.input_wells:
            if len(well.sample_tags) == 0:
                raise ValueError(f"Input well {well.position} has no samples.")
            for output_position in well.output_positions:
                if _split_ref(output_position, output_plates[0]) not in output_key_set:
                    raise ValueError(f"Output well {output_position} is not defined.")
        if "missing-sample" in [t for well in execution.input_wells for t in well.sample_tags]:
            raise ValueError("Samples not found: missing-sample")
        procedure = self.procedures[tag]
        outputs_per_sample = {}
        for well in execution.input_wells:
            for output_position in well.output_positions:
                for sample_tag in well.sample_tags:
                    outputs_per_sample.setdefault(sample_tag, set()).add(output_position)
        min_outputs = procedure.min_output_wells_per_sample if procedure.min_output_wells_per_sample is not None else 1
        max_outputs = procedure.max_output_wells_per_sample
        for sample_tag, sample_outputs in sorted(outputs_per_sample.items()):
            if len(sample_outputs) < min_outputs:
                raise ValueError(f"Sample {sample_tag} is transferred to {len(sample_outputs)} output wells, but the "
                                 f"procedure requires at least {min_outputs} output wells per sample.")
            if max_outputs is not None and len(sample_outputs) > max_outputs:
                raise ValueError(f"Sample {sample_tag} is transferred to {len(sample_outputs)} output wells, but the "
                                 f"procedure requires at most {max_outputs} output wells per sample.")
        responsible_user_tag = execution.responsible_user_tag or user_tag
        if responsible_user_tag == "missing-user":
            raise ValueError("Responsible user not found: missing-user")
        all_metrics = list(execution.output_well_metrics) + list(execution.input_well_metrics or [])
        for metric in all_metrics:
            side_wells = execution.output_wells if metric.side == "OUTPUT" else execution.input_wells
            side_plates = output_plates if metric.side == "OUTPUT" else input_plates
            side_name = "output" if metric.side == "OUTPUT" else "input"
            metric_plate = getattr(metric, "plate_tag", None) or side_plates[0]
            if (metric_plate, metric.position) not in {(_well_plate(w, side_plates[0]), w.position) for w in side_wells}:
                raise ValueError(f"Metrics were given for a non-defined {side_name} well: "
                                 f"{metric_plate}:{metric.position}")
            if metric.trait_tag not in ["trait-ugul", "trait-ph"]:
                raise ValueError(f"Traits not found: {metric.trait_tag}")
        input_sample_tags = [sample_tag for well in execution.input_wells for sample_tag in well.sample_tags]
        self.execution_counter = getattr(self, "execution_counter", 0) + 1
        execution_tag = f"exec-{self.execution_counter}"
        self.executions[execution_tag] = ProcedureExecutionModel(
            tag=execution_tag, procedure_tag=tag,
            input_plate_tag=execution.input_plate_tag, output_plate_tag=execution.output_plate_tag,
            input_plate_tags=input_plates, output_plate_tags=output_plates,
            user_tag=user_tag, responsible_user_tag=responsible_user_tag,
            created_at=4.0, status="RUNNING", done_submission_tags=[],
            input_well_metrics=[{"trait_tag": m.trait_tag, "attribute_tag": "att_concentration", "value": m.value}
                                for m in (execution.input_well_metrics or [])],
            input_wells=[{"position": w.position, "plate_tag": _well_plate(w, input_plates[0]),
                          "row_index": 0, "column_index": 0,
                          "sample_tags": w.sample_tags, "output_positions": w.output_positions,
                          "metrics": [{"trait_tag": m.trait_tag, "attribute_tag": "att_concentration", "value": m.value}
                                       for m in (execution.input_well_metrics or [])
                                       if m.position == w.position]}
                         for w in execution.input_wells],
            output_wells=[{"position": w.position, "plate_tag": _well_plate(w, output_plates[0]),
                           "row_index": 0, "column_index": 0,
                           "sample_tags": sorted({sample_tag for input_well in execution.input_wells
                                                   for sample_tag in input_well.sample_tags
                                                   for output_ref in input_well.output_positions
                                                   if _split_ref(output_ref, output_plates[0])
                                                   == (_well_plate(w, output_plates[0]), w.position)}),
                           "condition_application_tags": w.condition_application_tags,
                           "metrics": [{"trait_tag": m.trait_tag, "attribute_tag": "att_concentration", "value": m.value}
                                       for m in execution.output_well_metrics if m.position == w.position]}
                          for w in execution.output_wells])
        return self.executions[execution_tag]

    def get_occupied_output_wells(self, plate_tag):
        blocks = (lambda exec_model: exec_model.status == "RUNNING"
                  or getattr(exec_model, "wells_blocked", exec_model.status == "SUCCEEDED"))
        return [well.position for exec_model in self.executions.values()
                for well in exec_model.output_wells
                if (_well_plate(well, exec_model.output_plate_tag
                                if not getattr(exec_model, "output_plate_tags", None)
                                else exec_model.output_plate_tags[0]) == plate_tag)
                and blocks(exec_model)]

    def get_draft_executions_wells(self, plate_tag):
        draft_wells = {}
        for exec_model in self.executions.values():
            if exec_model.status != "DRAFT":
                continue
            if exec_model.input_plate_tag == plate_tag:
                for well in exec_model.input_wells:
                    draft_wells.setdefault(well.position, []).append(exec_model.tag)
            if exec_model.output_plate_tag == plate_tag:
                for well in exec_model.output_wells:
                    draft_wells.setdefault(well.position, []).append(exec_model.tag)
        return draft_wells

    def create_execution_draft(self, tag, user_tag):
        if tag not in self.procedures:
            raise KeyError("Modular procedure not found.")
        if self.procedures[tag].status != "PUBLISHED":
            raise ValueError("Only published modular procedures can be executed.")
        self.execution_counter = getattr(self, "execution_counter", 0) + 1
        execution_tag = f"draft-{self.execution_counter}"
        model = ProcedureExecutionModel(
            tag=execution_tag, procedure_tag=tag, input_plate_tag=None, output_plate_tag=None,
            user_tag=user_tag, responsible_user_tag=user_tag, created_at=3.0,
            status="DRAFT", wells_blocked=False, done_submission_tags=[])
        self.executions[execution_tag] = model
        return model

    def update_execution_draft(self, execution_tag, design_update, user_tag):
        if execution_tag not in self.executions:
            raise KeyError("Procedure execution not found.")
        execution = self.executions[execution_tag]
        if execution.status != "DRAFT":
            raise ValueError("Only draft executions can be set up — a started execution is immutable.")
        if design_update.input_plate_tag == "missing-plate" or design_update.output_plate_tag == "missing-plate":
            raise ValueError("Plate not found.")
        input_plates = _design_plates(design_update, "input")
        output_plates = _design_plates(design_update, "output")
        if any(t == "missing-plate" for t in input_plates + output_plates):
            raise ValueError("Plate not found.")
        input_keys = [(_well_plate(w, input_plates[0]), w.position) for w in design_update.input_wells]
        output_keys = {(_well_plate(w, output_plates[0]), w.position) for w in design_update.output_wells}
        if len(set(input_keys)) != len(input_keys) or len(output_keys) != len(design_update.output_wells):
            raise ValueError("Duplicate well positions are not allowed.")
        for well in design_update.input_wells:
            if len(well.sample_tags) == 0:
                raise ValueError(f"Input well {well.position} has no samples.")
            for output_position in well.output_positions:
                if _split_ref(output_position, output_plates[0]) not in output_keys:
                    raise ValueError(f"Output well {output_position} is not defined.")
        responsible_user_tag = design_update.responsible_user_tag or user_tag
        self.executions[execution_tag] = ProcedureExecutionModel(
            tag=execution_tag, procedure_tag=execution.procedure_tag,
            input_plate_tag=design_update.input_plate_tag, output_plate_tag=design_update.output_plate_tag,
            input_plate_tags=input_plates, output_plate_tags=output_plates,
            user_tag=execution.user_tag, responsible_user_tag=responsible_user_tag,
            created_at=execution.created_at, status="DRAFT", wells_blocked=False, done_submission_tags=[],
            input_wells=[{"position": w.position, "plate_tag": _well_plate(w, input_plates[0]),
                          "row_index": 0, "column_index": 0,
                          "sample_tags": w.sample_tags, "output_positions": w.output_positions}
                         for w in design_update.input_wells],
            output_wells=[{"position": w.position, "plate_tag": _well_plate(w, output_plates[0]),
                           "row_index": 0, "column_index": 0,
                           "sample_tags": sorted({sample_tag for input_well in design_update.input_wells
                                                   for sample_tag in input_well.sample_tags
                                                   for output_ref in input_well.output_positions
                                                   if _split_ref(output_ref, output_plates[0])
                                                   == (_well_plate(w, output_plates[0]), w.position)}),
                           "condition_application_tags": w.condition_application_tags}
                          for w in design_update.output_wells])
        return self.executions[execution_tag]

    def start_execution(self, execution_tag, user_tag):
        if execution_tag not in self.executions:
            raise KeyError("Procedure execution not found.")
        execution = self.executions[execution_tag]
        if execution.status != "DRAFT":
            raise ValueError("Only draft executions can be started.")
        if len(execution.input_wells) == 0 or len(execution.output_wells) == 0:
            raise ValueError("The draft has no design yet — save the plates, samples and transfer map first.")
        blocks = (lambda exec_model: exec_model.status == "RUNNING"
                  or getattr(exec_model, "wells_blocked", exec_model.status == "SUCCEEDED"))
        output_plate_tags = list(getattr(execution, "output_plate_tags", None) or []) or \
            ([execution.output_plate_tag] if execution.output_plate_tag else [])
        occupied = [(_well_plate(well, (list(getattr(exec_model, "output_plate_tags", None) or [])
                                         or [exec_model.output_plate_tag])[0]), well.position)
                    for exec_model in self.executions.values()
                    for well in exec_model.output_wells
                    if exec_model.tag != execution_tag
                    and (list(getattr(exec_model, "output_plate_tags", None) or [])
                         or [exec_model.output_plate_tag])[0] in output_plate_tags
                    and blocks(exec_model)]
        own = {(_well_plate(w, output_plate_tags[0]), w.position) for w in execution.output_wells}
        conflicts = sorted({f"{plate}:{pos}" for plate, pos in set(occupied) & own})
        if len(conflicts) > 0:
            raise ValueError(f"Output wells on {conflicts[0].split(':')[0]} already used by another execution: "
                             f"{', '.join(sorted({c.split(':')[1] for c in conflicts}))}")
        self.executions[execution_tag].status = "RUNNING"
        self.executions[execution_tag].wells_blocked = True
        self.executions[execution_tag].user_tag = user_tag
        return self.executions[execution_tag]

    def delete_execution_draft(self, execution_tag, user_tag):
        if execution_tag not in self.executions:
            raise KeyError("Procedure execution not found.")
        if self.executions[execution_tag].status != "DRAFT":
            raise ValueError("Only draft executions can be deleted — a started execution is part of the recorded history.")
        del self.executions[execution_tag]
        return True

    def finish_execution(self, execution_tag, outcome, user_tag, comment=None, block_output_wells=None):
        if execution_tag not in self.executions:
            raise KeyError("Procedure execution not found.")
        if outcome not in ("SUCCEEDED", "FAILED", "ABORTED"):
            raise ValueError("Outcome must be SUCCEEDED, FAILED or ABORTED.")
        execution = self.executions[execution_tag]
        if outcome == execution.status:
            raise ValueError(f"This procedure execution is already in state {execution.status}.")
        if execution.status == "DRAFT":
            raise ValueError("This procedure execution is still a draft — start it before confirming an outcome.")
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
                def _plates(exec_model, side):
                    tags = list(getattr(exec_model, f"{side}_plate_tags", None) or [])
                    primary = getattr(exec_model, f"{side}_plate_tag")
                    return tags if len(tags) > 0 else ([primary] if primary else [])
                for well in execution.input_wells:
                    if sample_tag in well.sample_tags:
                        entries.append({"procedure_tag": execution.procedure_tag, "execution_tag": tag,
                                         "status": execution.status or "RUNNING", "created_at": execution.created_at,
                                         "position": well.position, "side": "INPUT",
                                         "plate_tag": _well_plate(well, _plates(execution, "input")[0])})
                for well in execution.output_wells:
                    if sample_tag in well.sample_tags:
                        entries.append({"procedure_tag": execution.procedure_tag, "execution_tag": tag,
                                         "status": execution.status or "RUNNING", "created_at": execution.created_at,
                                         "position": well.position, "side": "OUTPUT",
                                         "plate_tag": _well_plate(well, _plates(execution, "output")[0])})
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
        if execution.status not in ("RUNNING", "SUCCEEDED"):
            raise ValueError("Measured values can only be recorded for a running or successfully finished execution.")
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

    def test_required_submission_state_on_insert_and_update(self, client):
        resp = client.post("/api/procedures/", json={
            "title": "Stateful", "description": "Only state 0 submissions",
            "required_submission_state": "SUBMITTED"})
        assert resp.status_code == 200
        assert resp.json()["required_submission_state"] == "SUBMITTED"
        # unknown state names are rejected
        resp = client.post("/api/procedures/", json={
            "title": "Stateful", "description": "Bad state", "required_submission_state": "NOT_A_STATE"})
        assert resp.status_code == 400
        assert "Unknown submission state" in resp.json()["detail"]
        # the field is optional and can be updated on a draft
        resp = client.patch("/api/procedures/proc-1", json={
            "title": "Updated", "description": "d", "required_submission_state": "PROCESSED"})
        assert resp.status_code == 200
        assert resp.json()["required_submission_state"] == "PROCESSED"
        resp = client.patch("/api/procedures/proc-1", json={
            "title": "Updated", "description": "d", "required_submission_state": None})
        assert resp.status_code == 200
        # storing it requires a valid state name as well
        resp = client.patch("/api/procedures/proc-1", json={
            "title": "Updated", "description": "d", "required_submission_state": "ALSO_NOT_A_STATE"})
        assert resp.status_code == 400

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


class TestModularProcedureRetirement:
    """Published procedures are content-hash immutable and never deleted; retiring is the way to
    end their life cycle: the content and hash stay, the procedure is greyed out and unusable."""

    def test_standard_user_rejected_on_retire(self):
        with _make_client(make_user(role=UserRolesEnum.STANDARD)) as c:
            resp = c.post("/api/procedures/proc-2/retire")
            assert resp.status_code == 403

    def test_retire_draft_rejected(self, client):
        resp = client.post("/api/procedures/proc-1/retire")
        assert resp.status_code == 400
        assert "Only published modular procedures can be retired" in resp.json()["detail"]

    def test_retire_published_and_twice_rejected(self, client):
        resp = client.post("/api/procedures/proc-2/retire")
        assert resp.status_code == 200
        assert resp.json()["status"] == "RETIRED"
        # the frozen content stays exactly as it was
        assert resp.json()["content_hash"]
        resp = client.post("/api/procedures/proc-2/retire")
        assert resp.status_code == 400
        assert "already retired" in resp.json()["detail"]

    def test_retired_procedure_cannot_be_linked_or_executed(self, client):
        client.post("/api/procedures/proc-2/retire")
        resp = client.post("/api/procedures/proc-2/link/subm-2")
        assert resp.status_code == 400
        assert "retired" in resp.json()["detail"]
        resp = client.post("/api/procedures/proc-2/execute", json={
            "input_plate_tag": "plate-1", "output_plate_tag": "plate-2",
            "input_wells": [{"position": "A1", "sample_tags": ["sample-1"], "output_positions": ["A1"]}],
            "output_wells": [{"position": "A1", "condition_application_tags": []}]})
        assert resp.status_code == 400

    def test_existing_link_can_still_be_marked_done(self, client):
        # subm-1 is pre-linked to proc-2 in the test fixture (and open)
        client.post("/api/procedures/proc-2/retire")
        resp = client.post("/api/procedures/proc-2/link/subm-1/done")
        assert resp.status_code == 200
        resp = client.delete("/api/procedures/proc-2/link/subm-1/done")
        assert resp.status_code == 200

    def test_new_version_blocked_for_retired(self, client):
        client.post("/api/procedures/proc-2/retire")
        resp = client.post("/api/procedures/proc-2/versions")
        assert resp.status_code == 400

    def test_retired_procedures_visible_in_queries(self, client):
        client.post("/api/procedures/proc-2/retire")
        resp = client.get("/api/procedures/q?status=RETIRED")
        assert resp.status_code == 200
        assert "proc-2" in resp.json()


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

    def test_executions_filtered_by_plate(self, client):
        self._execute_two_submissions(client)
        client.post("/api/procedures/proc-2/execute", json={
            "input_plate_tag": "plate-1", "output_plate_tag": "plate-3",
            "input_wells": [{"position": "D1", "sample_tags": ["sample-2"], "output_positions": ["D1"]}],
            "output_wells": [{"position": "D1", "condition_application_tags": []}]})
        # a plate fragment matches executions whose input or output plate contains it
        resp = client.get("/api/procedures/executions/q", params={"search_plate_tag": "plate-3"})
        assert resp.status_code == 200
        assert [summary["tag"] for summary in resp.json()] == ["exec-2"]
        resp = client.get("/api/procedures/executions/q", params={"search_plate_tag": "PLATE-1"})
        assert resp.status_code == 200
        assert len(resp.json()) == 2
        # combination with the state filter
        resp = client.get("/api/procedures/executions/q",
            params={"search_plate_tag": "plate-3", "status": "RUNNING"})
        assert resp.status_code == 200
        assert [summary["tag"] for summary in resp.json()] == ["exec-2"]
        # a fragment that matches nothing returns an empty list
        resp = client.get("/api/procedures/executions/q", params={"search_plate_tag": "plate-9"})
        assert resp.status_code == 200
        assert resp.json() == []

    def test_query_executions_by_procedure_tag(self, client):
        resp = client.get("/api/procedures/executions/q", params={"search_procedure_tag": "proc-2"})
        assert resp.status_code == 200
        assert len(resp.json()) == 0
        resp = client.get("/api/procedures/executions/q")
        assert resp.status_code == 200
        assert len(resp.json()) == 0
        client.post("/api/procedures/proc-2/execute", json={
            "input_plate_tag": "plate-1", "output_plate_tag": "plate-2",
            "input_wells": [{"position": "A1", "sample_tags": ["sample-1"], "output_positions": ["A1"]}],
            "output_wells": [{"position": "A1", "condition_application_tags": []}]})
        resp = client.get("/api/procedures/executions/q", params={"search_procedure_tag": "PROC-2"})
        assert resp.status_code == 200
        summaries = resp.json()
        assert len(summaries) == 1
        assert summaries[0]["procedure_tag"] == "proc-2"
        resp = client.get("/api/procedures/executions/q", params={"search_procedure_tag": "proc-9"})
        assert resp.status_code == 200
        assert resp.json() == []
    def test_summaries_include_plateless_drafts(self, client):
        # drafts without a saved design have no plates yet - the overview must list them, not crash
        draft_tag = client.post("/api/procedures/proc-2/executions/draft").json()["tag"]
        resp = client.get("/api/procedures/executions/q")
        assert resp.status_code == 200
        by_tag = {summary["tag"]: summary for summary in resp.json()}
        assert by_tag[draft_tag]["input_plate_tag"] is None
        assert by_tag[draft_tag]["output_plate_tag"] is None
        assert by_tag[draft_tag]["status"] == "DRAFT"

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

class TestModularProcedureSetupExtras:
    """PubMed references and the per-sample output well bounds (mirroring vs N-fold duplication)."""

    def test_pubmed_ids_stored_and_returned(self, client):
        resp = client.post("/api/procedures/", json={
            "title": "With references", "description": "",
            "pubmed_ids": ["12345678", "87654321"]})
        assert resp.status_code == 200
        tag = resp.json()["tag"]
        resp = client.get(f"/api/procedures/{tag}")
        assert resp.json()["pubmed_ids"] == ["12345678", "87654321"]

    def test_pubmed_ids_editable_on_draft_and_frozen_on_publish(self, client):
        resp = client.post("/api/procedures/", json={
            "title": "Reference editing", "description": "", "pubmed_ids": ["11111111"]})
        tag = resp.json()["tag"]
        resp = client.patch(f"/api/procedures/{tag}", json={
            "title": "Reference editing", "description": "", "pubmed_ids": ["22222222"]})
        assert resp.status_code == 200
        assert client.get(f"/api/procedures/{tag}").json()["pubmed_ids"] == ["22222222"]
        client.post(f"/api/procedures/{tag}/publish")
        resp = client.patch(f"/api/procedures/{tag}", json={
            "title": "Reference editing", "description": "", "pubmed_ids": ["33333333"]})
        assert resp.status_code == 400

    def test_multiplicity_bounds_validated(self, client):
        resp = client.post("/api/procedures/", json={
            "title": "Bounds", "description": "", "min_output_wells_per_sample": 0})
        assert resp.status_code == 400
        resp = client.post("/api/procedures/", json={
            "title": "Bounds", "description": "",
            "min_output_wells_per_sample": 8, "max_output_wells_per_sample": 4})
        assert resp.status_code == 400

    def test_declared_mirroring_rejects_duplication(self, client):
        """A procedure that declares itself mirroring (exactly one output well per sample)
        rejects executions that split a sample into several output wells; without declared
        bounds (the default) any transfer map is allowed."""
        resp = client.post("/api/procedures/", json={
            "title": "Mirroring", "description": "",
            "min_output_wells_per_sample": 1, "max_output_wells_per_sample": 1})
        tag = resp.json()["tag"]
        client.post(f"/api/procedures/{tag}/publish")
        # splitting into two output wells is rejected
        resp = client.post(f"/api/procedures/{tag}/execute", json={
            "input_plate_tag": "plate-1", "output_plate_tag": "plate-2",
            "input_wells": [{"position": "A1", "sample_tags": ["sample-1"], "output_positions": ["A1", "B1"]}],
            "output_wells": [{"position": "A1", "condition_application_tags": []},
                             {"position": "B1", "condition_application_tags": []}]})
        assert resp.status_code == 400
        assert "at most" in resp.json()["detail"]
        # mirroring works
        resp = client.post(f"/api/procedures/{tag}/execute", json={
            "input_plate_tag": "plate-1", "output_plate_tag": "plate-2",
            "input_wells": [{"position": "A1", "sample_tags": ["sample-1"], "output_positions": ["A1"]}],
            "output_wells": [{"position": "A1", "condition_application_tags": []}]})
        assert resp.status_code == 200
        # undeclared procedures keep allowing any transfer map (backwards compatible)
        resp = client.post("/api/procedures/proc-2/execute", json={
            "input_plate_tag": "plate-1", "output_plate_tag": "plate-unused",
            "input_wells": [{"position": "A1", "sample_tags": ["sample-1"], "output_positions": ["A1", "B1"]}],
            "output_wells": [{"position": "A1", "condition_application_tags": []},
                             {"position": "B1", "condition_application_tags": []}]})
        assert resp.status_code == 200

    def test_n_fold_duplication_fractionation(self, client):
        """A fractionation module with exactly 8 output wells per sample."""
        resp = client.post("/api/procedures/", json={
            "title": "Fractionation", "description": "",
            "min_output_wells_per_sample": 8, "max_output_wells_per_sample": 8})
        tag = resp.json()["tag"]
        client.post(f"/api/procedures/{tag}/publish")
        # two fractions only -> rejected
        resp = client.post(f"/api/procedures/{tag}/execute", json={
            "input_plate_tag": "plate-1", "output_plate_tag": "plate-2",
            "input_wells": [{"position": "A1", "sample_tags": ["sample-1"], "output_positions": ["A1", "B1"]}],
            "output_wells": [{"position": "A1", "condition_application_tags": []},
                             {"position": "B1", "condition_application_tags": []}]})
        assert resp.status_code == 400
        # 8 fractions -> allowed
        resp = client.post(f"/api/procedures/{tag}/execute", json={
            "input_plate_tag": "plate-1", "output_plate_tag": "plate-2",
            "input_wells": [{"position": "A1", "sample_tags": ["sample-1"],
                             "output_positions": [f"{chr(ord('A') + i)}1" for i in range(8)]}],
            "output_wells": [{"position": f"{chr(ord('A') + i)}1", "condition_application_tags": []}
                             for i in range(8)]})
        assert resp.status_code == 200

    def test_bounded_duplication_range(self, client):
        """min < max allows a variable number of output wells per sample within the range."""
        resp = client.post("/api/procedures/", json={
            "title": "Range", "description": "",
            "min_output_wells_per_sample": 1, "max_output_wells_per_sample": 4})
        tag = resp.json()["tag"]
        client.post(f"/api/procedures/{tag}/publish")
        resp = client.post(f"/api/procedures/{tag}/execute", json={
            "input_plate_tag": "plate-1", "output_plate_tag": "plate-2",
            "input_wells": [{"position": "A1", "sample_tags": ["sample-1"],
                             "output_positions": ["A1", "B1", "C1", "D1", "E1"]}],
            "output_wells": [{"position": p, "condition_application_tags": []}
                             for p in ["A1", "B1", "C1", "D1", "E1"]]})
        assert resp.status_code == 400
        assert "at most" in resp.json()["detail"]
        resp = client.post(f"/api/procedures/{tag}/execute", json={
            "input_plate_tag": "plate-1", "output_plate_tag": "plate-2",
            "input_wells": [{"position": "A1", "sample_tags": ["sample-1"], "output_positions": ["A1", "B1", "C1"]}],
            "output_wells": [{"position": p, "condition_application_tags": []}
                             for p in ["A1", "B1", "C1"]]})
        assert resp.status_code == 200


DESIGN_PAYLOAD = {
    "input_plate_tag": "plate-1", "output_plate_tag": "plate-2",
    "input_wells": [{"position": "A1", "sample_tags": ["sample-1"], "output_positions": ["A1"]}],
    "output_wells": [{"position": "A1", "condition_application_tags": []}],
}


class TestModularProcedurePlateOccupancy:
    def test_occupied_wells_of_plate(self, client):
        client.post("/api/procedures/proc-2/execute", json=DESIGN_PAYLOAD)
        resp = client.get("/api/procedures/plates/plate-2/occupied")
        assert resp.status_code == 200
        assert resp.json() == ["A1"]
        # drafts do not block anything
        draft_tag = client.post("/api/procedures/proc-2/executions/draft").json()["tag"]
        client.put(f"/api/procedures/executions/{draft_tag}", json=dict(DESIGN_PAYLOAD, output_plate_tag="plate-3"))
        resp = client.get("/api/procedures/plates/plate-3/occupied")
        assert resp.status_code == 200
        assert resp.json() == []


class TestModularProcedureExecutionDrafts:
    """Draft executions: a backend-generated ID, a setup that can be saved and continued, and a
    start that runs the full validation — drafts never block wells until they start."""

    def test_draft_lifecycle_create_save_start(self, client):
        resp = client.post("/api/procedures/proc-2/executions/draft")
        assert resp.status_code == 200
        draft = resp.json()
        assert draft["status"] == "DRAFT"
        assert draft["input_plate_tag"] is None
        assert draft["wells_blocked"] is False
        # the creating user is the default responsible user
        assert draft["responsible_user_tag"] == "abcdefgh"
        # finishing a draft is not possible
        resp = client.post(f"/api/procedures/executions/{draft['tag']}/finish", json={"outcome": "SUCCEEDED"})
        assert resp.status_code == 400
        assert "draft" in resp.json()["detail"]
        # save the design
        resp = client.put(f"/api/procedures/executions/{draft['tag']}", json=DESIGN_PAYLOAD)
        assert resp.status_code == 200
        assert resp.json()["status"] == "DRAFT"
        assert resp.json()["output_wells"][0]["sample_tags"] == ["sample-1"]
        # ... and go back to it: a second save replaces the design
        resp = client.put(f"/api/procedures/executions/{draft['tag']}", json=DESIGN_PAYLOAD)
        assert resp.status_code == 200
        # a draft without a design cannot start
        resp = client.post("/api/procedures/proc-2/executions/draft")
        empty_draft_tag = resp.json()["tag"]
        resp = client.post(f"/api/procedures/executions/{empty_draft_tag}/start")
        assert resp.status_code == 400
        # starting the saved draft runs it
        resp = client.post(f"/api/procedures/executions/{draft['tag']}/start")
        assert resp.status_code == 200
        assert resp.json()["status"] == "RUNNING"
        assert resp.json()["wells_blocked"] is True
        # started executions are immutable and undeletable
        resp = client.put(f"/api/procedures/executions/{draft['tag']}", json=DESIGN_PAYLOAD)
        assert resp.status_code == 400
        resp = client.delete(f"/api/procedures/executions/{draft['tag']}")
        assert resp.status_code == 400

    def test_draft_allows_partial_save_without_plates(self, client):
        draft_tag = client.post("/api/procedures/proc-2/executions/draft").json()["tag"]
        # a draft can be saved at any stage: without plates, wells and metrics nothing has to be defined yet
        resp = client.put(f"/api/procedures/executions/{draft_tag}", json={"responsible_user_tag": "abcdefgh"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "DRAFT"
        assert body["input_plate_tag"] is None
        assert body["output_plate_tag"] is None
        assert body["responsible_user_tag"] == "abcdefgh"
        assert body["input_wells"] == []
        # a partial draft still cannot start
        resp = client.post(f"/api/procedures/executions/{draft_tag}/start")
        assert resp.status_code == 400

    def test_output_values_recordable_after_success(self, client):
        # a procedure declaring a result attribute measured at the output wells
        resp = client.post("/api/procedures/", json={
            "title": "With results", "description": "d", "output_attribute_tags": ["att_concentration"]})
        assert resp.status_code == 200
        result_procedure_tag = resp.json()["tag"]
        client.post(f"/api/procedures/{result_procedure_tag}/publish")
        resp = client.post(f"/api/procedures/{result_procedure_tag}/execute", json=DESIGN_PAYLOAD)
        assert resp.status_code == 200
        running_tag = resp.json()["tag"]
        # result values can be recorded while the execution runs ...
        resp = client.post(f"/api/procedures/executions/{running_tag}/metrics",
            json=[{"position": "A1", "trait_tag": "trait-ugul", "value": 2.5}])
        assert resp.status_code == 200
        well = [w for w in resp.json()["output_wells"] if w["position"] == "A1"][0]
        assert well["metrics"][-1]["trait_tag"] == "trait-ugul"
        assert well["metrics"][-1]["value"] == 2.5
        # ... and after it was confirmed successful (values often arrive only then)
        client.post(f"/api/procedures/executions/{running_tag}/finish", json={"outcome": "SUCCEEDED"})
        resp = client.post(f"/api/procedures/executions/{running_tag}/metrics",
            json=[{"position": "A1", "trait_tag": "trait-ugul", "value": 3.25}])
        assert resp.status_code == 200
        # drafts do not accept measured values (their values come with the saved design)
        draft_tag = client.post("/api/procedures/proc-2/executions/draft").json()["tag"]
        resp = client.post(f"/api/procedures/executions/{draft_tag}/metrics",
            json=[{"position": "A1", "trait_tag": "trait-ugul", "value": 1}])
        assert resp.status_code == 400
        assert "running or successfully finished" in resp.json()["detail"]

    def test_draft_rejects_invalid_design(self, client):
        draft_tag = client.post("/api/procedures/proc-2/executions/draft").json()["tag"]
        # transfer to a non-defined output well
        resp = client.put(f"/api/procedures/executions/{draft_tag}", json={
            **DESIGN_PAYLOAD,
            "input_wells": [{"position": "A1", "sample_tags": ["sample-1"], "output_positions": ["B1"]}]})
        assert resp.status_code == 400
        assert "not defined" in resp.json()["detail"]

    def test_drafts_do_not_block_wells_until_start(self, client):
        draft_tag = client.post("/api/procedures/proc-2/executions/draft").json()["tag"]
        resp = client.put(f"/api/procedures/executions/{draft_tag}", json=DESIGN_PAYLOAD)
        assert resp.status_code == 200
        # another execution may take the same output wells while the draft is not started
        resp = client.post("/api/procedures/proc-2/execute", json={
            **DESIGN_PAYLOAD, "output_plate_tag": "plate-2"})
        assert resp.status_code == 200
        # starting the draft now conflicts with the running execution on those wells
        resp = client.post(f"/api/procedures/executions/{draft_tag}/start")
        assert resp.status_code == 400
        assert "already used" in resp.json()["detail"]

    def test_draft_wells_are_reported_for_conflict_warnings(self, client):
        # drafts block nothing, but their wells are reported so setups can warn about conflicts
        draft_tag = client.post("/api/procedures/proc-2/executions/draft").json()["tag"]
        resp = client.put(f"/api/procedures/executions/{draft_tag}", json=DESIGN_PAYLOAD)
        assert resp.status_code == 200
        resp = client.get("/api/procedures/plates/plate-1/drafts/occupied")
        assert resp.status_code == 200
        assert resp.json() == {"A1": [draft_tag]}
        resp = client.get("/api/procedures/plates/plate-2/drafts/occupied")
        assert resp.status_code == 200
        assert resp.json() == {"A1": [draft_tag]}
        # a started execution is no draft and is not reported here
        client.post(f"/api/procedures/executions/{draft_tag}/start")
        resp = client.get("/api/procedures/plates/plate-2/drafts/occupied")
        assert resp.status_code == 200
        assert resp.json() == {}

    def test_draft_can_be_deleted(self, client):
        draft_tag = client.post("/api/procedures/proc-2/executions/draft").json()["tag"]
        resp = client.delete(f"/api/procedures/executions/{draft_tag}")
        assert resp.status_code == 200
        assert resp.json() is True
        resp = client.get(f"/api/procedures/executions/{draft_tag}")
        assert resp.status_code == 404

    def test_draft_of_unpublished_procedure_rejected(self, client):
        resp = client.post("/api/procedures/proc-1/executions/draft")
        assert resp.status_code == 400

    def test_standard_user_rejected_on_draft_creation(self):
        with _make_client(make_user(role=UserRolesEnum.STANDARD)) as c:
            resp = c.post("/api/procedures/proc-2/executions/draft")
            assert resp.status_code == 403


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


class TestModularProcedureMultiPlateExecutions:
    """Multi-plate executions: a design can hold several input and several output plates - the
    samples (or the produced wells) do not always fit on a single plate. Wells carry the plate they
    are on; transfer targets on additional output plates are plate-qualified ("plate:position")."""

    MULTI_PLATE_PAYLOAD = {
        "input_plate_tag": "plate-1", "output_plate_tag": "plate-2",
        "additional_input_plate_tags": ["plate-1b"],
        "additional_output_plate_tags": ["plate-2b"],
        "input_wells": [
            {"position": "A1", "sample_tags": ["sample-1"], "output_positions": ["A1"]},
            # the same position on another input plate is not a duplicate
            {"position": "A1", "plate_tag": "plate-1b", "sample_tags": ["sample-3"],
             "output_positions": ["plate-2b:A1"]},
        ],
        "output_wells": [
            {"position": "A1"},
            {"position": "A1", "plate_tag": "plate-2b"},
        ],
    }

    def test_execute_multi_plate_design(self, client):
        resp = client.post("/api/procedures/proc-2/execute", json=self.MULTI_PLATE_PAYLOAD)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["input_plate_tags"] == ["plate-1", "plate-1b"]
        assert body["output_plate_tags"] == ["plate-2", "plate-2b"]
        assert body["input_plate_tag"] == "plate-1"
        assert body["output_plate_tag"] == "plate-2"
        input_by_plate = {(w["plate_tag"], w["position"]) for w in body["input_wells"]}
        assert input_by_plate == {("plate-1", "A1"), ("plate-1b", "A1")}
        output_by_plate = {(w["plate_tag"], w["position"], tuple(sorted(w["sample_tags"])))
                           for w in body["output_wells"]}
        assert output_by_plate == {("plate-2", "A1", ("sample-1",)),
                                   ("plate-2b", "A1", ("sample-3",))}

    def test_plate_positions_are_scoped_per_plate(self, client):
        # a real duplicate (same plate) is rejected
        resp = client.post("/api/procedures/proc-2/execute", json={
            **DESIGN_PAYLOAD,
            "input_wells": [{"position": "A1", "sample_tags": ["sample-1"], "output_positions": ["A1", "A2"]}],
            "output_wells": [{"position": "A1"}, {"position": "A1"}]})
        assert resp.status_code == 400
        assert "Duplicate" in resp.json()["detail"]
        # ... but with several output plates the same position is legal (two different wells)
        resp = client.post("/api/procedures/proc-2/execute", json=self.MULTI_PLATE_PAYLOAD)
        assert resp.status_code == 200

    def test_unknown_additional_plate_rejected(self, client):
        resp = client.post("/api/procedures/proc-2/execute", json={
            **DESIGN_PAYLOAD, "additional_output_plate_tags": ["missing-plate"]})
        assert resp.status_code == 400
        assert "Plate not found" in resp.json()["detail"]

    def test_well_on_undeclared_plate_rejected(self, client):
        resp = client.post("/api/procedures/proc-2/execute", json={
            **DESIGN_PAYLOAD,
            "output_wells": [{"position": "A1", "plate_tag": "plate-1b"}]})
        assert resp.status_code == 400

    def test_occupancy_is_per_plate(self, client):
        # occupy A1 on plate-2 ...
        resp = client.post("/api/procedures/proc-2/execute", json=DESIGN_PAYLOAD)
        assert resp.status_code == 200
        resp = client.get("/api/procedures/plates/plate-2/occupied")
        assert resp.status_code == 200
        assert resp.json() == ["A1"]
        resp = client.get("/api/procedures/plates/plate-2b/occupied")
        assert resp.status_code == 200
        assert resp.json() == []
        # ... the same position on the additional output plate is still free
        additional_only = {
            "input_plate_tag": "plate-1", "output_plate_tag": "plate-2",
            "additional_output_plate_tags": ["plate-2b"],
            "input_wells": [{"position": "B2", "sample_tags": ["sample-3"],
                             "output_positions": ["plate-2b:A1"]}],
            "output_wells": [{"position": "A1", "plate_tag": "plate-2b"}]}
        resp = client.post("/api/procedures/proc-2/execute", json=additional_only)
        assert resp.status_code == 200
        # but a second run on the same additional plate conflicts
        resp = client.post("/api/procedures/proc-2/execute", json=additional_only)
        assert resp.status_code == 400
        assert "already used" in resp.json()["detail"]

    def test_draft_multi_plate_design_can_be_saved_and_started(self, client):
        draft_tag = client.post("/api/procedures/proc-2/executions/draft").json()["tag"]
        resp = client.put(f"/api/procedures/executions/{draft_tag}", json=self.MULTI_PLATE_PAYLOAD)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["output_plate_tags"] == ["plate-2", "plate-2b"]
        assert body["status"] == "DRAFT"
        assert client.get("/api/procedures/plates/plate-2/occupied").json() == []
        resp = client.post(f"/api/procedures/executions/{draft_tag}/start")
        assert resp.status_code == 200
        assert client.get("/api/procedures/plates/plate-2b/occupied").json() == ["A1"]

    def test_multi_plate_sample_locations(self, client):
        resp = client.post("/api/procedures/proc-2/execute", json=self.MULTI_PLATE_PAYLOAD)
        assert resp.status_code == 200
        resp = client.get("/api/procedures/submissions/subm-2/wells")
        assert resp.status_code == 200
        wells = [well for location in resp.json() for well in location["wells"]]
        assert sorted((w["plate_tag"], w["position"], w["side"]) for w in wells) == \
            [("plate-1b", "A1", "INPUT"), ("plate-2b", "A1", "OUTPUT")]

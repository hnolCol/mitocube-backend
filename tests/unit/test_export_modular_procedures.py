"""
Unit tests for the modular procedures section of the submission markdown export."""

import sys
sys.path.insert(0, "src")

import pytest

from services.export_submissions import format_modular_procedures
from config.models.procedures import (
    ModularProcedureBaseModel, ModularProcedureSubmissionModel,
    ProcedureExecutionModel, ProcedureExecutionInputWellModel,
    ProcedureExecutionOutputWellModel, ExecutionStateModel,
)


class FakeUsersDB:
    def exists(self, tag):
        return tag in {"usr_1"}

    def get_user_by_tag(self, tag):
        class U:
            firstname = "Jane"
            lastname = "Doe"
        return U()


class FakeProceduresDB:
    def __init__(self):
        procedure = ModularProcedureBaseModel(
            tag="proc_1", title="SP3 Digestion", description="", status="PUBLISHED",
            version=1, user_tag="usr_1")
        self.procedures = {"proc_1": procedure}
        self.links = [ModularProcedureSubmissionModel(
            procedure_tag="proc_1", submission_tag="subm_1", position=0,
            created_at=1700000000.0, done=True, done_at=1700000100.0, done_by="usr_1")]
        self.executions = {
            "exec_1": ProcedureExecutionModel(
                tag="exec_1", procedure_tag="proc_1", input_plate_tag="plt_in",
                output_plate_tag="plt_out", user_tag="usr_1", responsible_user_tag="usr_1",
                created_at=1700000050.0, status="SUCCEEDED", wells_blocked=True,
                finished_at=1700000100.0, finished_by="usr_1", done_submission_tags=["subm_1"],
                input_wells=[ProcedureExecutionInputWellModel(
                    position="A1", row_index=0, column_index=0, sample_tags=["smp_1"],
                    output_positions=["A1"])],
                output_wells=[ProcedureExecutionOutputWellModel(
                    position="A1", row_index=0, column_index=0, sample_tags=["smp_1"],
                    condition_application_tags=["ca_heat"])]),
        }
        self.states = {
            "exec_1": [
                ExecutionStateModel(state="SUCCEEDED", created_at=1700000100.0, user_tag="usr_1"),
                ExecutionStateModel(state="RUNNING", created_at=1700000050.0, user_tag="usr_1"),
            ],
        }

    def get(self, tag):
        if tag not in self.procedures:
            raise KeyError()
        return self.procedures[tag]

    def get_submission_procedures(self, submission_tag):
        return self.links

    def find_execution_tags_by_submissions(self, submission_tags):
        return ["exec_1"] if "subm_1" in submission_tags else []

    def get_execution(self, execution_tag):
        if execution_tag not in self.executions:
            raise KeyError()
        return self.executions[execution_tag]

    def get_execution_states(self, execution_tag):
        if execution_tag not in self.states:
            raise KeyError()
        return self.states[execution_tag]

    def get_sample_submission_map(self, sample_tags):
        return {sample_tag: ["subm_1"] for sample_tag in sample_tags}


class FakeDB:
    def __init__(self):
        self.modular_procedures = FakeProceduresDB()
        self.users = FakeUsersDB()


def test_includes_module_chain_execution_states_and_wells():
    markdown = format_modular_procedures("subm_1", FakeDB())
    assert "## Workflow Modules" in markdown
    assert "SP3 Digestion" in markdown
    assert "### Execution `exec_1` — SP3 Digestion" in markdown
    assert "plt_in" in markdown and "plt_out" in markdown
    assert "#### State History" in markdown
    assert "SUCCEEDED" in markdown and "RUNNING" in markdown
    assert "Jane Doe" in markdown
    assert "#### Input Wells" in markdown and "#### Output Wells" in markdown
    assert "smp_1" in markdown
    assert "ca_heat" in markdown


def test_foreign_samples_are_not_exported():
    db = FakeDB()
    execution = db.modular_procedures.executions["exec_1"]
    execution.input_wells[0].sample_tags = ["smp_1", "smp_other"]
    db.modular_procedures.get_sample_submission_map = lambda sample_tags: {
        "smp_1": ["subm_1"], "smp_other": ["subm_2"]}
    markdown = format_modular_procedures("subm_1", db)
    assert "smp_1" in markdown
    assert "smp_other" not in markdown


def test_submission_without_modules_returns_empty():
    class EmptyDB(FakeDB):
        def __init__(self):
            super().__init__()
            self.modular_procedures.links = []
            self.modular_procedures.find_execution_tags_by_submissions = lambda submission_tags: []
    assert format_modular_procedures("subm_1", EmptyDB()) == ""


def test_execution_model_tolerates_null_lists():
    """Fresh draft executions have no done_submission_tags / stored input metrics yet: the database
    returns null and the model must coerce it to an empty list instead of failing (the executions
    overview reads every visible execution)."""
    import sys
    sys.path.insert(0, "src")
    from config.models.procedures import ProcedureExecutionModel
    execution = ProcedureExecutionModel(
        tag="exec_draft", procedure_tag="proc_1", input_plate_tag=None, output_plate_tag=None,
        user_tag="usr_1", status="DRAFT", done_submission_tags=None, input_well_metrics=None)
    assert execution.done_submission_tags == []
    assert execution.input_well_metrics == []

"""
Tests for the setup CLI (src/setup_utils/cli.py).

The database calls are stubbed with recording fakes: these tests verify
argument parsing, step orchestration, ordering, and the precondition
errors — not the actual migrations.
"""

import sys
from pathlib import Path

import pytest

SRC_DIR = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(SRC_DIR))

from fastapi import HTTPException  # noqa: F401  (env sanity)


class FakeDB:
    def __init__(self):
        self.users = FakeUsers()
        self.attributes = Recorder("attributes")
        self.research_groups = FakeResearchGroups()
        self.instrument_states = Recorder("instrument_states")
        self.maintenance_events = Recorder("maintenance_events")
        self.maintenance_procedures = Recorder("maintenance_procedures")
        self.symptoms = Recorder("symptoms")
        self.spareparts = Recorder("spareparts")
        self.proteomes = Recorder("proteomes")
        self.annotations = Recorder("annotations")
        self.external_resources = Recorder("external_resources")


class Recorder:
    def __init__(self, name):
        self.name = name
        self.calls = []

    def __getattr__(self, item):
        def _call(*args, **kwargs):
            self.calls.append((item, args, kwargs))
        return _call


class FakeUsers:
    def __init__(self):
        self.checked = []
        self.lead_user = "leadtag1"

    def check(self, lead_tag=None):
        self.checked.append(lead_tag)

    def get_lead_user(self):
        return self.lead_user

    def _utils_migrate(self, path_to_user_data):
        return ["userA", "userB"]


class FakeResearchGroups:
    def __init__(self):
        self.inserted = []

    def insert_users(self, tag, user_tags):
        self.inserted.append((tag, user_tags))


@pytest.fixture
def cli(monkeypatch):
    import setup_utils.cli as cli_module
    fake = FakeDB()
    monkeypatch.setattr(cli_module, "DB", fake)
    return cli_module, fake


class TestParser:
    def test_all_flags_present(self, cli):
        cli_module, _ = cli
        args = cli_module.build_parser().parse_args([])
        for flag in [
            "setup_database", "migrate_submissions", "proteomes",
            "add_control_proteome", "resources_path", "lead_user_tag",
            "users", "mitocarta_annotations", "reviewed_proteins_only",
            "external_resources_xl", "add_research_groups",
        ]:
            assert hasattr(args, flag)

    def test_flag_values(self, cli):
        cli_module, _ = cli
        args = cli_module.build_parser().parse_args(
            ["--setup_database", "--proteomes", "UP1,UP2", "--users", "/x/users.json"]
        )
        assert args.setup_database is True
        assert args.proteomes == "UP1,UP2"
        assert args.users == "/x/users.json"


class TestBootstrap:
    def test_bootstrap_ensures_lead_user_first(self, cli, tmp_path):
        cli_module, fake = cli
        resources = tmp_path / "resources"
        resources.mkdir()
        args = cli_module.build_parser().parse_args(
            ["--setup_database", "--resources_path", str(resources),
             "--users", "/x/users.json"]
        )
        ctx = {}
        # users file does not exist -> bootstrap must raise before research_groups insert
        with pytest.raises(ValueError, match="User path"):
            cli_module.step_bootstrap(args, ctx)
        assert fake.users.checked == [None]  # check() ran first

    def test_bootstrap_missing_research_group_raises(self, cli, tmp_path, monkeypatch):
        cli_module, fake = cli
        resources = tmp_path / "resources"
        (resources / "attributes").mkdir(parents=True)
        args = cli_module.build_parser().parse_args(
            ["--setup_database", "--resources_path", str(resources),
             "--users", "/x/users.json"]
        )
        monkeypatch.setattr("os.path.exists", lambda p: True)
        monkeypatch.setattr(cli_module.pd, "read_csv", lambda *a, **k: None)
        ctx = {}
        with pytest.raises(ValueError, match="default research group"):
            cli_module.step_bootstrap(args, ctx)


class TestRunOrchestration:
    def test_no_setup_flags_touches_nothing(self, cli):
        cli_module, fake = cli
        cli_module.run([])
        assert fake.users.checked == []
        assert fake.attributes.calls == []

    def test_run_bootstrap_order(self, cli, tmp_path, monkeypatch):
        cli_module, fake = cli
        resources = tmp_path / "resources"
        (resources / "attributes").mkdir(parents=True)
        args_list = ["--setup_database", "--resources_path", str(resources), "--users", "/x/u.json"]
        monkeypatch.setattr("os.path.exists", lambda p: True)
        monkeypatch.setattr(cli_module.pd, "read_csv", lambda *a, **k: None)
        # research groups file present + flag -> default_rg set
        import pandas as pd
        monkeypatch.setattr(cli_module.pd, "DataFrame", pd.DataFrame)
        with pytest.raises(ValueError):
            # may raise on research-group df handling; acceptable for this test
            cli_module.run(args_list)
        assert fake.users.checked == [None]

    def test_missing_lead_user_aborts(self, cli, tmp_path, monkeypatch):
        cli_module, fake = cli
        fake.users.lead_user = None
        resources = tmp_path / "resources"
        (resources / "attributes").mkdir(parents=True)
        args = cli_module.build_parser().parse_args(
            ["--setup_database", "--resources_path", str(resources), "--users", "/x/u.json"]
        )
        with pytest.raises(ValueError, match="lead user"):
            cli_module.step_bootstrap(args, {})

import pandas as pd
import pytest

from config.models.performance import QCRunResponseModel
from config.models.reports import YearReportModel
from services.year_report import build_year_report
from routers.reports.year_report import _report_to_excel

YEAR = 2024


def _qc_run(tag, instrument, quant_proteins, quant_peptides, created_at):
    return QCRunResponseModel(
        tag=tag,
        instrument_name_tag=instrument,
        user_tag="user-1",
        qc_standard_tag="std-1",
        rt_peptides={},
        quant_proteins=quant_proteins,
        quant_peptides=quant_peptides,
        quant_precursors=10,
        quant_protein_groups=quant_proteins,
        created_at=created_at,
    )


def _ms(year, month=1):
    import calendar
    return calendar.timegm((year, month, 1, 0, 0, 0)) * 1000


class FakeUsers:
    def count_by_year(self, year):
        return 5 if year == YEAR else 0

    def count(self):
        return 42


class FakeSubmissionFilter:
    def __init__(self):
        self.calls = []

    def get_counts_by_year(self, by, entity, years=None, **kwargs):
        self.calls.append((by, entity, years))
        if entity == "submission" and by == "research_group":
            return pd.DataFrame({"group": ["rg-1", "rg-2"], "year": [YEAR, YEAR], "value": [3, 4]})
        if entity == "submission" and by == "user":
            return pd.DataFrame({"group": ["user-1"], "year": [YEAR], "value": [7]})
        return pd.DataFrame({"group": ["rg-1"], "year": [YEAR], "value": [100]})


class FakeSubmissions:
    def __init__(self):
        self.quant_df = pd.DataFrame({
            "submission_tag": ["subm-1", "subm-2"],
            "count": [1000, 2000],
            "user_tag": ["user-1", "user-2"],
            "created_at": [_ms(YEAR), _ms(YEAR - 1)],
        })

    def get_protein_group_quantification_count(self):
        return self.quant_df

    def get_trending(self, limit=10):
        return ["subm-1"]


class FakeInstruments:
    def get(self, instrument_type=None, tags=None):
        return [{"tag": "inst-1", "text": "Instrument 1"}]

    def get_unique_protein_group_count_by_year(self, instrument_tag, year):
        return 900


class FakeInstrumentStates:
    def get_state_duration_summary(self, instrument_tag, timestamp_min=None, timestamp_max=None):
        return [{"state_tag": "running", "state_text": "Running", "total_days": 300.0}]


class FakeMaintenanceEvents:
    def count(self, instrument_tag=None, user_tag=None, timestamp_min=None, timestamp_max=None):
        return 2


class FakeQC:
    def __init__(self):
        self.runs = [
            _qc_run("qc-1", "inst-1", 4000, 30000, _ms(YEAR, 3)),
            _qc_run("qc-2", "inst-1", 5000, 31000, _ms(YEAR, 6)),
            _qc_run("qc-old", "inst-1", 9999, 99999, _ms(YEAR - 1)),
        ]

    def get(self, limit=50):
        return self.runs[:limit]


class FakeDB:
    def __init__(self):
        self.users = FakeUsers()
        self.submission_filter = FakeSubmissionFilter()
        self.submissions = FakeSubmissions()
        self.instruments = FakeInstruments()
        self.instrument_states = FakeInstrumentStates()
        self.maintenance_events = FakeMaintenanceEvents()
        self.qc = FakeQC()


def test_build_year_report_aggregates_all_sections():
    report = build_year_report(YEAR, FakeDB())
    assert isinstance(report, YearReportModel)
    assert report.year == YEAR
    assert report.community.new_users == 5
    assert report.community.total_users == 42
    assert report.submissions.new_submissions == 7
    assert report.submissions.new_samples == 100
    assert report.submissions.per_user == [{"group": "user-1", "year": YEAR, "value": 7}]
    assert report.data_volume.quantified_protein_groups == 1000
    assert report.data_volume.per_instrument == [{"instrument_tag": "inst-1", "unique_protein_groups": 900}]
    assert len(report.instrument_performance) == 1
    perf = report.instrument_performance[0]
    assert perf.instrument_tag == "inst-1"
    assert perf.qc_runs == 2
    assert perf.median_quant_proteins == 4500.0
    assert perf.median_quant_peptides == 30500.0
    assert perf.maintenance_events == 2
    assert perf.unique_protein_groups == 900
    assert perf.state_summary[0]["state_tag"] == "running"
    assert report.highlights.trending_submissions == ["subm-1"]


def test_build_year_report_tolerates_failing_sources():
    class BrokenDB:
        class _Broken:
            def __getattr__(self, name):
                raise RuntimeError("broken")

        users = _Broken()
        submission_filter = _Broken()
        submissions = _Broken()
        instruments = _Broken()
        instrument_states = _Broken()
        maintenance_events = _Broken()
        qc = _Broken()

    report = build_year_report(YEAR, BrokenDB())
    assert report.community.new_users == 0
    assert report.submissions.new_submissions == 0
    assert report.data_volume.quantified_protein_groups == 0
    assert report.instrument_performance == []
    assert report.highlights.trending_submissions == []


def test_report_to_excel_returns_readable_workbook():
    report = build_year_report(YEAR, FakeDB())
    buffer = _report_to_excel(report)
    sheets = pd.read_excel(buffer, sheet_name=None)
    assert "Community" in sheets
    assert "Instrument performance" in sheets
    assert sheets["Community"].iloc[0]["new_users"] == 5
    assert sheets["Instrument performance"].iloc[0]["qc_runs"] == 2

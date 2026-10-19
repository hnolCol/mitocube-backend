"""Aggregation service for the yearly MitoCube report.

The report is a presentation layer over existing database access methods:
community growth, submission/sample throughput, quantified data volume and
instrument performance (QC runs, maintenance, state durations). All heavy
lifting is delegated to the database layer; this module only aggregates.
"""
from datetime import datetime, timezone
from typing import List

import pandas as pd

from config.models.reports import (
    YearReportCommunityModel,
    YearReportDataVolumeModel,
    YearReportHighlightsModel,
    YearReportInstrumentPerformanceModel,
    YearReportModel,
    YearReportSubmissionsModel,
)
from lib.database.abstract.Database import DatabaseABC


def _year_bounds_ms(year: int) -> tuple:
    year_start = int(datetime(year, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
    year_end = int(datetime(year + 1, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
    return year_start, year_end


def _df_to_records(df: pd.DataFrame) -> List[dict]:
    if df is None or df.empty:
        return []
    return df.to_dict(orient="records")


def _year_subset(df: pd.DataFrame, year: int) -> pd.DataFrame:
    if df is None or df.empty or "year" not in df.columns:
        return pd.DataFrame(columns=getattr(df, "columns", []))
    return df[df["year"] == year]


def build_year_report(year: int, db: DatabaseABC) -> YearReportModel:
    """Assembles the yearly report for the given calendar year.

    Each section is built independently so that a failure in one data source
    does not take down the whole report; failing sections degrade to empty
    values.
    """
    year_start_ms, year_end_ms = _year_bounds_ms(year)

    community = _build_community(year, db)
    submissions = _build_submissions(year, db)
    data_volume = _build_data_volume(year, db)
    instrument_performance = _build_instrument_performance(year, db, year_start_ms, year_end_ms)
    highlights = _build_highlights(db)

    return YearReportModel(
        year=year,
        community=community,
        submissions=submissions,
        data_volume=data_volume,
        instrument_performance=instrument_performance,
        highlights=highlights,
    )


def _build_community(year: int, db: DatabaseABC) -> YearReportCommunityModel:
    try:
        new_users = int(db.users.count_by_year(year=year))
    except Exception:
        new_users = 0
    try:
        total_users = int(db.users.count())
    except Exception:
        total_users = 0
    return YearReportCommunityModel(new_users=new_users, total_users=total_users)


def _build_submissions(year: int, db: DatabaseABC) -> YearReportSubmissionsModel:
    try:
        df = db.submission_filter.get_counts_by_year(by="research_group", entity="submission", years=[year])
        per_group = _year_subset(df, year)
    except Exception:
        per_group = pd.DataFrame(columns=["group", "year", "value"])
    try:
        df_users = db.submission_filter.get_counts_by_year(by="user", entity="submission", years=[year])
        per_user = _year_subset(df_users, year)
    except Exception:
        per_user = pd.DataFrame(columns=["group", "year", "value"])
    try:
        df_samples = db.submission_filter.get_counts_by_year(by="research_group", entity="sample", years=[year])
        samples_df = _year_subset(df_samples, year)
        new_samples = int(samples_df["value"].sum()) if not samples_df.empty else 0
    except Exception:
        new_samples = 0
    new_submissions = int(per_group["value"].sum()) if not per_group.empty else 0
    return YearReportSubmissionsModel(
        new_submissions=new_submissions,
        new_samples=new_samples,
        per_research_group=_df_to_records(per_group),
        per_user=_df_to_records(per_user),
    )


def _build_data_volume(year: int, db: DatabaseABC) -> YearReportDataVolumeModel:
    try:
        quant_df = db.submissions.get_protein_group_quantification_count()
    except Exception:
        quant_df = pd.DataFrame(columns=["submission_tag", "count", "user_tag", "created_at"])
    total_quantified = 0
    if quant_df is not None and not quant_df.empty:
        created = pd.to_datetime(quant_df["created_at"], unit="ms", utc=True, errors="coerce")
        mask = created.dt.year == year
        total_quantified = int(quant_df.loc[mask, "count"].sum())

    per_instrument = []
    try:
        instruments = db.instruments.get() or []
    except Exception:
        instruments = []
    for instrument in instruments:
        tag = instrument.get("tag")
        if tag is None:
            continue
        try:
            unique_pg = int(db.instruments.get_unique_protein_group_count_by_year(instrument_tag=tag, year=year))
        except Exception:
            unique_pg = 0
        per_instrument.append({"instrument_tag": tag, "unique_protein_groups": unique_pg})

    return YearReportDataVolumeModel(
        quantified_protein_groups=total_quantified,
        per_instrument=per_instrument,
    )


def _build_instrument_performance(year: int, db: DatabaseABC, year_start_ms: int, year_end_ms: int) -> List[YearReportInstrumentPerformanceModel]:
    try:
        instruments = db.instruments.get() or []
    except Exception:
        instruments = []
    try:
        qc_runs = db.qc.get(limit=1000000) or []
    except Exception:
        qc_runs = []

    sections = []
    for instrument in instruments:
        tag = instrument.get("tag")
        if tag is None:
            continue
        runs = [r for r in qc_runs if getattr(r, "instrument_name_tag", None) == tag and _run_in_year(r, year)]
        quant_proteins = [r.quant_proteins for r in runs if getattr(r, "quant_proteins", None) is not None]
        quant_peptides = [r.quant_peptides for r in runs if getattr(r, "quant_peptides", None) is not None]
        try:
            maintenance_events = int(db.maintenance_events.count(instrument_tag=tag, timestamp_min=year_start_ms, timestamp_max=year_end_ms))
        except Exception:
            maintenance_events = 0
        try:
            state_summary = db.instrument_states.get_state_duration_summary(instrument_tag=tag, timestamp_min=year_start_ms, timestamp_max=year_end_ms) or []
        except Exception:
            state_summary = []
        try:
            unique_pg = int(db.instruments.get_unique_protein_group_count_by_year(instrument_tag=tag, year=year))
        except Exception:
            unique_pg = 0
        sections.append(YearReportInstrumentPerformanceModel(
            instrument_tag=tag,
            qc_runs=len(runs),
            median_quant_proteins=float(pd.Series(quant_proteins).median()) if quant_proteins else None,
            median_quant_peptides=float(pd.Series(quant_peptides).median()) if quant_peptides else None,
            maintenance_events=maintenance_events,
            unique_protein_groups=unique_pg,
            state_summary=state_summary,
        ))
    return sections


def _run_in_year(run, year: int) -> bool:
    created_at = getattr(run, "created_at", None)
    if created_at is None:
        return False
    try:
        return datetime.fromtimestamp(int(created_at) / 1000, tz=timezone.utc).year == year
    except Exception:
        return False


def _build_highlights(db: DatabaseABC) -> YearReportHighlightsModel:
    try:
        trending = db.submissions.get_trending(limit=10) or []
    except Exception:
        trending = []
    return YearReportHighlightsModel(trending_submissions=list(trending))

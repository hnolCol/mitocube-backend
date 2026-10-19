from typing import List
import io

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response, StreamingResponse

from lib.database.Database import get_db
from lib.database.abstract.Database import DatabaseABC
from config.models.reports import YearReportModel
from config.models.user import UserModel
from services.users import is_user_at_least_curator
from services.year_report import build_year_report

router = APIRouter(
    prefix="/api/reports",
    tags=["Reports"],
)


@router.get("/years", summary="Returns the calendar years that have reportable data. Requires at least curator rights.")
def get_report_years(user: UserModel = Depends(is_user_at_least_curator), db: DatabaseABC = Depends(get_db)) -> List[int]:
    years = set()
    try:
        df = db.submission_filter.get_counts_by_year(by="research_group", entity="submission")
        if df is not None and not df.empty and "year" in df.columns:
            years.update(int(y) for y in df["year"].dropna())
    except Exception:
        pass
    return sorted(years)


@router.get("/year/{year}", summary="Returns the aggregated yearly report as JSON. Requires at least curator rights.")
def get_year_report(year: int, user: UserModel = Depends(is_user_at_least_curator), db: DatabaseABC = Depends(get_db)) -> YearReportModel:
    if year < 2000 or year > 2100:
        raise HTTPException(status_code=422, detail=f"Invalid year {year}.")
    return build_year_report(year=year, db=db)


@router.get("/year/{year}/download", summary="Downloads the yearly report as an Excel workbook (format=xlsx) or Markdown file (format=md). Requires at least curator rights.")
def download_year_report(year: int, format: str = "xlsx", user: UserModel = Depends(is_user_at_least_curator), db: DatabaseABC = Depends(get_db)):
    if year < 2000 or year > 2100:
        raise HTTPException(status_code=422, detail=f"Invalid year {year}.")
    if format not in ("xlsx", "md"):
        raise HTTPException(status_code=422, detail=f"Unsupported format '{format}'. Use 'xlsx' or 'md'.")
    report = build_year_report(year=year, db=db)
    if format == "md":
        return Response(
            content=_report_to_markdown(report),
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="mitocube_year_report_{year}.md"'},
        )
    try:
        buffer = _report_to_excel(report)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate the report workbook: {str(e)}")
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="mitocube_year_report_{year}.xlsx"'},
    )


def _report_to_markdown(report: YearReportModel) -> str:
    lines = [f"# MitoCube Year Report {report.year}", ""]

    lines += ["## Community", ""]
    lines += [f"- New users: {report.community.new_users}",
              f"- Total users: {report.community.total_users}", ""]

    lines += ["## Submissions", ""]
    lines += [f"- New submissions: {report.submissions.new_submissions}",
              f"- New samples: {report.submissions.new_samples}", ""]
    if report.submissions.per_research_group:
        lines += ["### New submissions per research group", "",
                  "| Research group | Submissions |", "| --- | --- |"]
        for row in report.submissions.per_research_group:
            lines.append(f"| {row.get('group', '')} | {row.get('value', 0)} |")
        lines.append("")
    if report.submissions.per_user:
        lines += ["### New submissions per user", "",
                  "| User | Submissions |", "| --- | --- |"]
        for row in report.submissions.per_user:
            lines.append(f"| {row.get('group', '')} | {row.get('value', 0)} |")
        lines.append("")

    lines += ["## Data volume", ""]
    lines += [f"- Protein group quantifications: {report.data_volume.quantified_protein_groups}"]
    if report.data_volume.per_instrument:
        lines += ["", "| Instrument | Unique protein groups |", "| --- | --- |"]
        for row in report.data_volume.per_instrument:
            lines.append(f"| {row.get('instrument_tag', '')} | {row.get('unique_protein_groups', 0)} |")
    lines.append("")

    if report.instrument_performance:
        lines += ["## Instrument performance", "",
                  "| Instrument | QC runs | Median quant. proteins | Median quant. peptides | Maintenance events | Unique protein groups |",
                  "| --- | --- | --- | --- | --- | --- |"]
        for s in report.instrument_performance:
            lines.append(
                f"| {s.instrument_tag} | {s.qc_runs} | {s.median_quant_proteins if s.median_quant_proteins is not None else ''}"
                f" | {s.median_quant_peptides if s.median_quant_peptides is not None else ''}"
                f" | {s.maintenance_events} | {s.unique_protein_groups} |"
            )
        lines.append("")

    if report.highlights.trending_submissions:
        lines += ["## Highlights", "", "Trending submissions:", ""]
        lines += [f"- {t}" for t in report.highlights.trending_submissions]
        lines.append("")

    return "\n".join(lines)


def _report_to_excel(report: YearReportModel) -> io.BytesIO:
    community_df = pd.DataFrame([report.community.model_dump()])
    submissions_df = pd.DataFrame(report.submissions.per_research_group)
    samples_df = pd.DataFrame(report.submissions.per_research_group)
    users_df = pd.DataFrame(report.submissions.per_user)
    instruments_df = pd.DataFrame([s.model_dump() for s in report.instrument_performance])
    if not instruments_df.empty:
        instruments_df = instruments_df.drop(columns=["state_summary"], errors="ignore")

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        community_df.to_excel(writer, sheet_name="Community", index=False)
        submissions_df.to_excel(writer, sheet_name="Submissions per group", index=False)
        users_df.to_excel(writer, sheet_name="Submissions per user", index=False)
        samples_df.to_excel(writer, sheet_name="Samples per group", index=False)
        instruments_df.to_excel(writer, sheet_name="Instrument performance", index=False)
        pd.DataFrame(report.highlights.model_dump()).to_excel(writer, sheet_name="Highlights", index=False)
    buffer.seek(0)
    return buffer

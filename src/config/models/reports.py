from typing import List, Optional
from pydantic import BaseModel


class YearReportCommunityModel(BaseModel):
    new_users: int
    total_users: int


class YearReportSubmissionsModel(BaseModel):
    new_submissions: int
    new_samples: int
    per_research_group: List[dict]
    per_user: List[dict]


class YearReportDataVolumeModel(BaseModel):
    quantified_protein_groups: int
    per_instrument: List[dict]


class YearReportInstrumentPerformanceModel(BaseModel):
    instrument_tag: str
    qc_runs: int
    median_quant_proteins: Optional[float] = None
    median_quant_peptides: Optional[float] = None
    maintenance_events: int
    unique_protein_groups: int
    state_summary: List[dict]


class YearReportHighlightsModel(BaseModel):
    trending_submissions: List[str]


class YearReportModel(BaseModel):
    year: int
    community: YearReportCommunityModel
    submissions: YearReportSubmissionsModel
    data_volume: YearReportDataVolumeModel
    instrument_performance: List[YearReportInstrumentPerformanceModel]
    highlights: YearReportHighlightsModel

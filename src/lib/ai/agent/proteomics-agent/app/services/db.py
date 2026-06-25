"""
Stand-in for your existing DB interfaces, so this project runs out of the box.

REPLACE THIS FILE'S CONTENTS with your actual DB module, or better: delete it
and change the import in app/agent/tools/proteomics_tools.py to point at your
real `DB` object (e.g. `from app.db import DB`). The shapes returned here
(dicts/lists of dicts) are what the tool layer expects — keep that contract
when you swap in the real implementation.
"""

from __future__ import annotations

_SUBMISSIONS = [
    {
        "submission_id": "SUB001",
        "title": "Plasma proteome in early-stage pancreatic cancer",
        "pi_name": "Dr. A. Müller",
        "organism": "Homo sapiens",
        "date_submitted": "2025-11-03",
        "n_samples": 42,
        "abstract": "LC-MS/MS profiling of plasma samples from early-stage PDAC patients vs. controls.",
        "instrument": "Orbitrap Exploris 480",
        "processing_status": "complete",
    },
    {
        "submission_id": "SUB002",
        "title": "Mouse liver proteome under caloric restriction",
        "pi_name": "Dr. R. Patel",
        "organism": "Mus musculus",
        "date_submitted": "2026-01-17",
        "n_samples": 18,
        "abstract": "Quantitative proteomics of liver tissue across caloric restriction timepoints.",
        "instrument": "timsTOF Pro",
        "processing_status": "complete",
    },
]

_PROTEINS = {
    "SUB001": [
        {"protein_id": "P1", "gene_name": "TP53", "accession": "P04637", "abundance": 8421.5, "n_peptides": 12, "coverage_pct": 41.2},
        {"protein_id": "P2", "gene_name": "ALB", "accession": "P02768", "abundance": 152033.1, "n_peptides": 31, "coverage_pct": 78.9},
    ],
    "SUB002": [
        {"protein_id": "P3", "gene_name": "Tp53", "accession": "P02340", "abundance": 3012.7, "n_peptides": 6, "coverage_pct": 22.0},
    ],
}


class _Submissions:
    def find(self, search_string: str = "") -> list[dict]:
        if not search_string:
            return list(_SUBMISSIONS)
        s = search_string.lower()
        return [
            sub for sub in _SUBMISSIONS
            if s in sub["title"].lower()
            or s in sub["pi_name"].lower()
            or s in sub["organism"].lower()
        ]

    def get(self, submission_id: str) -> dict | None:
        return next((s for s in _SUBMISSIONS if s["submission_id"] == submission_id), None)


class _Proteins:
    def find_by_submission(
        self, submission_id: str, min_abundance: float | None = None, limit: int = 50
    ) -> list[dict]:
        rows = _PROTEINS.get(submission_id, [])
        if min_abundance is not None:
            rows = [r for r in rows if r["abundance"] >= min_abundance]
        return sorted(rows, key=lambda r: -r["abundance"])[:limit]

    def compare_across_submissions(
        self, gene_name: str, submission_ids: list[str]
    ) -> list[dict]:
        out = []
        for sid in submission_ids:
            match = next(
                (r for r in _PROTEINS.get(sid, []) if r["gene_name"].lower() == gene_name.lower()),
                None,
            )
            out.append(
                {
                    "submission_id": sid,
                    "found": match is not None,
                    "abundance": match["abundance"] if match else None,
                }
            )
        return out


class _DB:
    submissions = _Submissions()
    proteins = _Proteins()


DB = _DB()

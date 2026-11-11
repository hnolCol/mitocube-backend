from __future__ import annotations
import re
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel


MODIFICATIONS_FILE = Path(__file__).resolve().parents[2] / "resources" / "modifications" / "modifications.txt"

MASS_TOLERANCE = 0.005

_MOD_PATTERN = re.compile(r"([A-Z])[\[\(]([^\]\)]+)[\]\)]")


class UniModModel(BaseModel):
    """A UniMod modification record (resources/modifications/modifications.txt)."""
    accession: int
    name: str
    description: str
    monoisotopic_mass: float
    average_mass: float
    composition: str


class ParsedModificationModel(BaseModel):
    """A modification parsed from an engine sequence string, e.g. PEPTS[Phospho]IDEK."""
    peptide_position: int  # 1-based position of the modified residue in the unmodified peptide sequence
    residue: str
    raw_modification: str  # the string as reported by the search engine
    unimod: Optional[UniModModel] = None


@lru_cache(maxsize=1)
def load_unimod() -> Dict[int, UniModModel]:
    """Loads the UniMod modifications file into a dict keyed by accession."""
    records: Dict[int, UniModModel] = {}
    with open(MODIFICATIONS_FILE, "r", encoding="utf-8", errors="replace") as f:
        header = f.readline()
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 6:
                continue
            accession, name, description, mono, avg, composition = parts[:6]
            records[int(accession)] = UniModModel(
                accession=int(accession),
                name=name.strip().strip('"'),
                description=description.strip().strip('"'),
                monoisotopic_mass=float(mono),
                average_mass=float(avg),
                composition=composition,
            )
    return records


def resolve_unimod(modification: str, residue: Optional[str] = None) -> UniModModel:
    """Resolves a modification string to a UniMod record. Accepts a UniMod accession
    (e.g. "21"), a UniMod interim name or description (case-insensitive, e.g. "Phospho"
    or "Phosphorylation") or a monoisotopic mass (e.g. "79.966331"). Raises a ValueError
    if the modification cannot be resolved unambiguously.
    """
    records = load_unimod()
    mod = modification.strip()
    if mod.isdigit() and int(mod) in records:
        return records[int(mod)]
    lowered = mod.lower()
    by_name = [r for r in records.values() if r.name.lower() == lowered or r.description.lower() == lowered]
    if len(by_name) == 1:
        return by_name[0]
    try:
        mass = float(mod)
    except ValueError:
        raise ValueError(f"Could not resolve modification '{modification}' to a UniMod entry.")
    exact = [r for r in records.values() if r.monoisotopic_mass == mass]
    if len(exact) == 1:
        return exact[0]
    by_mass = [r for r in records.values() if abs(r.monoisotopic_mass - mass) <= MASS_TOLERANCE]
    if len(by_mass) == 1:
        return by_mass[0]
    raise ValueError(f"Could not resolve modification '{modification}' to a unique UniMod entry.")


def parse_modified_sequence(sequence: str) -> tuple[str, List[ParsedModificationModel]]:
    """Parses a search engine modified sequence (e.g. PEPTS[Phospho]IDEK, PEPTS(79.966331)IDEK)
    into the unmodified sequence and a list of parsed modifications with their 1-based
    peptide positions. Each parsed modification is resolved to UniMod.
    """
    clean_parts = []
    mods: List[ParsedModificationModel] = []
    last = 0
    for match in _MOD_PATTERN.finditer(sequence):
        clean_parts.append(sequence[last:match.start(1)] + match.group(1))
        residue = match.group(1)
        raw_mod = match.group(2)
        peptide_position = sum(len(p) for p in clean_parts)
        mods.append(ParsedModificationModel(
            peptide_position=peptide_position,
            residue=residue,
            raw_modification=raw_mod,
            unimod=resolve_unimod(raw_mod, residue=residue),
        ))
        last = match.end()
    clean_parts.append(sequence[last:])
    clean_sequence = "".join(clean_parts)
    if not clean_sequence:
        raise ValueError(f"Sequence '{sequence}' does not contain an unmodified peptide sequence.")
    return clean_sequence, mods


def ptm_site_tag(protein_tag: str, position: int, modification: str) -> str:
    """Derives the PTMSite tag from the protein tag, the 1-based protein position and the
    (normalized, uppercased) modification name, e.g. P12345_S473_PHOSPHO."""
    return f"{protein_tag}_{position}_{modification.upper()}"

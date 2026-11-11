import pytest

from services.modifications import (
    load_unimod,
    parse_modified_sequence,
    ptm_site_tag,
    resolve_unimod,
)
from config.models.ptm_precursors import PTMPrecursorInsertModel


class TestResolveUnimod:
    def test_resolve_by_accession(self):
        unimod = resolve_unimod("21")
        assert unimod.accession == 21
        assert unimod.name == "Phospho"
        assert unimod.monoisotopic_mass == pytest.approx(79.966331)

    def test_resolve_by_name_case_insensitive(self):
        assert resolve_unimod("phospho").accession == 21
        assert resolve_unimod("Phosphorylation").accession == 21

    def test_resolve_by_mass(self):
        assert resolve_unimod("79.966331").accession == 21
        assert resolve_unimod("79.97").accession == 21

    def test_unknown_modification_raises(self):
        with pytest.raises(ValueError):
            resolve_unimod("not-a-modification")

    def test_registry_is_loaded(self):
        assert len(load_unimod()) > 1000


class TestParseModifiedSequence:
    def test_bracket_name(self):
        clean, mods = parse_modified_sequence("PEPTS[Phospho]IDEK")
        assert clean == "PEPTSIDEK"
        assert len(mods) == 1
        assert mods[0].peptide_position == 5
        assert mods[0].residue == "S"
        assert mods[0].raw_modification == "Phospho"
        assert mods[0].unimod.accession == 21

    def test_paren_mass(self):
        clean, mods = parse_modified_sequence("PEPTS(79.966331)IDEK")
        assert clean == "PEPTSIDEK"
        assert mods[0].unimod.accession == 21

    def test_double_phospho_yields_two_mods(self):
        clean, mods = parse_modified_sequence("PEPTS[Phospho]IDEK[Phospho]")
        assert clean == "PEPTSIDEK"
        assert len(mods) == 2
        assert [m.peptide_position for m in mods] == [5, 9]
        assert mods[1].residue == "K"
        assert all(m.unimod.accession == 21 for m in mods)

    def test_unmodified_sequence(self):
        clean, mods = parse_modified_sequence("PEPTSIDEK")
        assert clean == "PEPTSIDEK"
        assert mods == []


class TestPTMPrecursorModel:
    def test_ptm_site_tags_single_and_double(self):
        precursor = PTMPrecursorInsertModel(
            tag="PEPTS[Phospho]IDEK.2",
            sequence="PEPTS[Phospho]IDEK",
            charge=2,
            protein_group_tags=["pg1"],
            protein_tag="P12345",
            modifications=[
                {"position": 473, "modification": "Phospho", "unimod_id": 21, "unimod_name": "Phospho"},
                {"position": 475, "modification": "Phospho", "unimod_id": 21, "unimod_name": "Phospho"},
            ],
        )
        assert precursor.ptm_site_tags() == ["P12345_473_PHOSPHO", "P12345_475_PHOSPHO"]

    def test_requires_at_least_one_modification(self):
        with pytest.raises(ValueError):
            PTMPrecursorInsertModel(
                tag="PEPTSIDEK.2",
                sequence="PEPTSIDEK",
                charge=2,
                protein_group_tags=["pg1"],
                protein_tag="P12345",
                modifications=[],
            )

    def test_duplicate_positions_rejected(self):
        with pytest.raises(ValueError):
            PTMPrecursorInsertModel(
                tag="PEPTS[Phospho]IDEK.2",
                sequence="PEPTS[Phospho]IDEK",
                charge=2,
                protein_group_tags=["pg1"],
                protein_tag="P12345",
                modifications=[
                    {"position": 473, "modification": "Phospho"},
                    {"position": 473, "modification": "Phospho"},
                ],
            )


def test_ptm_site_tag_helper():
    assert ptm_site_tag("P12345", 473, "Phospho") == "P12345_473_PHOSPHO"

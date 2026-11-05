import numpy as np
import pandas as pd
import pytest
from scipy import stats as scipy_stats

from lib.data.ranking.FeatureRanking import FeatureRanking
from lib.database.neo4j.Submission import build_combined_attribute_rows


def _quantification_frame(rows):
    return pd.DataFrame(
        rows,
        columns=["protein_group_tag", "value", "attribute_tag", "ca_tags", "sample_tag"],
    )


def test_build_combined_attribute_rows_combines_all_attribute_pairs():
    df = _quantification_frame([
        ["pg_1", 10.0, "att_genotype", "geno_ko", "s1"],
        ["pg_1", 10.0, "att_treatment", "ca_treatment", "s1"],
        ["pg_1", 11.0, "att_genotype", "geno_wt", "s2"],
        ["pg_1", 11.0, "att_treatment", "ca_dmso", "s2"],
    ])

    combined = build_combined_attribute_rows(df=df)

    assert not combined.empty
    assert set(combined["attribute_tag"]) == {"att_genotype__att_treatment"}
    s1 = combined[combined["sample_tag"] == "s1"].iloc[0]
    assert s1["ca_tags"] == "ca_treatment,geno_ko"
    assert s1["value"] == 10.0
    s2 = combined[combined["sample_tag"] == "s2"].iloc[0]
    assert s2["ca_tags"] == "ca_dmso,geno_wt"


def test_build_combined_attribute_rows_skips_samples_missing_one_attribute():
    df = _quantification_frame([
        ["pg_1", 10.0, "att_genotype", "geno_ko", "s1"],
        ["pg_1", 10.0, "att_treatment", "ca_treatment", "s1"],
        ["pg_1", 11.0, "att_genotype", "geno_wt", "s2"],
    ])

    combined = build_combined_attribute_rows(df=df)

    assert set(combined["sample_tag"]) == {"s1"}


def test_build_combined_attribute_rows_returns_empty_frame_without_pairs():
    df = _quantification_frame([
        ["pg_1", 10.0, "att_genotype", "geno_ko", "s1"],
    ])

    combined = build_combined_attribute_rows(df=df)

    assert combined.empty
    assert list(combined.columns) == ["protein_group_tag", "value", "attribute_tag", "ca_tags", "sample_tag"]


def test_compute_metrics_flags_exclusive_protein_in_combined_attribute():
    df = _quantification_frame([
        ["pg_1", 10.0, "att_genotype__att_treatment", "ca_dmso,geno_ko", "s1"],
        ["pg_1", 10.5, "att_genotype__att_treatment", "ca_dmso,geno_ko", "s2"],
        ["pg_1", 11.0, "att_genotype__att_treatment", "ca_treatment,geno_ko", "s3"],
        ["pg_1", 11.5, "att_genotype__att_treatment", "ca_treatment,geno_ko", "s4"],
        ["pg_2", 20.0, "att_genotype__att_treatment", "ca_dmso,geno_ko", "s1"],
        ["pg_2", 20.0, "att_genotype__att_treatment", "ca_dmso,geno_ko", "s2"],
        ["pg_2", 21.0, "att_genotype__att_treatment", "ca_treatment,geno_ko", "s3"],
        ["pg_2", 21.0, "att_genotype__att_treatment", "ca_treatment,geno_ko", "s4"],
    ])

    result = FeatureRanking().compute_metrics(df=df)

    exclusive = result[result["protein_group_tag"] == "pg_1"]
    assert len(exclusive) == 1
    assert exclusive.iloc[0]["exclusively"] == False  # noqa: E712
    non_exclusive = result[result["protein_group_tag"] == "pg_2"]
    assert non_exclusive.iloc[0]["exclusively"] == False  # noqa: E712


def test_compute_metrics_flags_exclusive_protein_across_combined_groups():
    df = _quantification_frame([
        ["pg_1", 10.0, "att_genotype__att_treatment", "ca_dmso,geno_ko", "s1"],
        ["pg_1", 10.5, "att_genotype__att_treatment", "ca_dmso,geno_ko", "s2"],
        ["pg_2", 20.0, "att_genotype__att_treatment", "ca_dmso,geno_ko", "s1"],
        ["pg_2", 20.5, "att_genotype__att_treatment", "ca_dmso,geno_ko", "s2"],
        ["pg_2", 21.0, "att_genotype__att_treatment", "ca_treatment,geno_ko", "s3"],
        ["pg_2", 21.5, "att_genotype__att_treatment", "ca_treatment,geno_ko", "s4"],
    ])

    result = FeatureRanking().compute_metrics(df=df)

    exclusive = result[result["protein_group_tag"] == "pg_1"].iloc[0]
    assert exclusive["exclusively"] == True  # noqa: E712
    assert exclusive["exclusively_ca_tags"] == ["ca_dmso,geno_ko"]
    non_exclusive = result[result["protein_group_tag"] == "pg_2"].iloc[0]
    assert non_exclusive["exclusively"] == False  # noqa: E712


def test_compute_metrics_drops_condition_application_groups_of_single_samples():
    df = _quantification_frame([
        ["pg_1", 10.0, "att_mouse_id", "mouse_1", "s1"],
        ["pg_1", 10.5, "att_mouse_id", "mouse_2", "s2"],
        ["pg_1", 11.0, "att_mouse_id", "mouse_3", "s3"],
        ["pg_2", 20.0, "att_mouse_id", "mouse_1", "s1"],
        ["pg_2", 20.5, "att_mouse_id", "mouse_2", "s2"],
        ["pg_2", 21.0, "att_mouse_id", "mouse_3", "s3"],
    ])

    result = FeatureRanking().compute_metrics(df=df)

    assert result.empty


def test_compute_metrics_keeps_exclusivity_when_group_has_two_samples():
    df = _quantification_frame([
        ["pg_1", 10.0, "att_treatment", "ca_dmso", "s1"],
        ["pg_1", 10.5, "att_treatment", "ca_dmso", "s2"],
        ["pg_1", np.nan, "att_treatment", "ca_treatment", "s3"],
        ["pg_1", np.nan, "att_treatment", "ca_treatment", "s4"],
    ])

    result = FeatureRanking().compute_metrics(df=df)

    exclusive = result.iloc[0]
    assert exclusive["exclusively"] == True  # noqa: E712
    assert exclusive["exclusively_ca_tags"] == ["ca_dmso"]


def test_compute_metrics_no_exclusivity_for_single_quantified_sample():
    df = _quantification_frame([
        ["pg_1", 10.0, "att_treatment", "ca_dmso", "s1"],
        ["pg_1", 10.5, "att_treatment", "ca_dmso", "s2"],
        ["pg_1", np.nan, "att_treatment", "ca_treatment", "s3"],
        ["pg_1", np.nan, "att_treatment", "ca_treatment", "s4"],
        ["pg_2", 20.0, "att_treatment", "ca_dmso", "s1"],
        ["pg_2", np.nan, "att_treatment", "ca_dmso", "s2"],
        ["pg_2", np.nan, "att_treatment", "ca_treatment", "s3"],
        ["pg_2", np.nan, "att_treatment", "ca_treatment", "s4"],
    ])

    result = FeatureRanking().compute_metrics(df=df)

    pg_2 = result[result["protein_group_tag"] == "pg_2"].iloc[0]
    assert pg_2["exclusively"] == False  # noqa: E712


def test_compute_metrics_missingness_uses_all_samples_of_attribute():
    df = _quantification_frame([
        ["pg_1", 10.0, "att_treatment", "ca_dmso", "s1"],
        ["pg_1", 10.5, "att_treatment", "ca_dmso", "s2"],
        ["pg_1", 11.0, "att_treatment", "ca_treatment", "s3"],
        ["pg_1", 11.5, "att_treatment", "ca_treatment", "s4"],
        ["pg_2", 20.0, "att_treatment", "ca_dmso", "s1"],
        ["pg_2", 21.0, "att_treatment", "ca_treatment", "s3"],
    ])

    result = FeatureRanking().compute_metrics(df=df)

    pg_1 = result[result["protein_group_tag"] == "pg_1"].iloc[0]
    assert pg_1["missingness"] == 0.0
    pg_2 = result[result["protein_group_tag"] == "pg_2"].iloc[0]
    assert pg_2["missingness"] == 0.5
    assert pg_2["quantified_in_samples"] == 2


def test_compute_metrics_sanitizes_infinite_anova_results():
    df = _quantification_frame([
        ["pg_1", 10.0, "att_treatment", "ca_dmso", "s1"],
        ["pg_1", 10.0, "att_treatment", "ca_dmso", "s2"],
        ["pg_1", 12.0, "att_treatment", "ca_treatment", "s3"],
        ["pg_1", 12.0, "att_treatment", "ca_treatment", "s4"],
    ])

    result = FeatureRanking().compute_metrics(df=df)

    row = result.iloc[0]
    assert np.isnan(row["F"])
    assert np.isnan(row["p_value"])
    assert np.isnan(row["cohen_f"])
    assert row["eta_squared"] == 1.0
    assert np.isfinite(row["score"])


def test_compute_metrics_gives_exclusive_proteins_a_score():
    df = _quantification_frame([
        ["pg_1", 10.0, "att_treatment", "ca_dmso", "s1"],
        ["pg_1", 10.5, "att_treatment", "ca_dmso", "s2"],
        ["pg_1", np.nan, "att_treatment", "ca_treatment", "s3"],
        ["pg_1", np.nan, "att_treatment", "ca_treatment", "s4"],
        ["pg_2", 20.0, "att_genotype", "geno_ko", "s1"],
        ["pg_2", 20.5, "att_genotype", "geno_ko", "s2"],
        ["pg_2", np.nan, "att_genotype", "geno_wt", "s3"],
        ["pg_2", np.nan, "att_genotype", "geno_wt", "s4"],
        ["pg_2", np.nan, "att_genotype", "geno_het", "s5"],
        ["pg_2", np.nan, "att_genotype", "geno_het", "s6"],
    ])

    result = FeatureRanking().compute_metrics(df=df)

    pg_1 = result[(result["protein_group_tag"] == "pg_1") & (result["attribute_tag"] == "att_treatment")].iloc[0]
    assert pg_1["exclusively"] == True  # noqa: E712
    assert pg_1["score"] == np.log10(2 + 1)
    pg_2 = result[(result["protein_group_tag"] == "pg_2") & (result["attribute_tag"] == "att_genotype")].iloc[0]
    assert pg_2["exclusively"] == True  # noqa: E712
    assert pg_2["score"] == np.log10(3 + 1)
    assert pg_2["score"] > pg_1["score"]


def test_compute_metrics_anova_excludes_single_observation_groups():
    df = _quantification_frame([
        ["pg_1", 10.0, "att_treatment", "ca_dmso", "s1"],
        ["pg_1", 10.2, "att_treatment", "ca_dmso", "s2"],
        ["pg_1", 10.4, "att_treatment", "ca_dmso", "s3"],
        ["pg_1", 12.0, "att_treatment", "ca_treatment", "s4"],
        ["pg_1", 12.2, "att_treatment", "ca_treatment", "s5"],
        ["pg_1", 15.0, "att_treatment", "ca_other", "s6"],
        ["pg_1", 15.1, "att_treatment", "ca_other", "s7"],
        ["pg_1", 30.0, "att_treatment", "ca_single", "s8"],
        ["pg_1", np.nan, "att_treatment", "ca_single", "s9"],
    ])

    result = FeatureRanking().compute_metrics(df=df)

    row = result.iloc[0]
    expected_f, expected_p = scipy_stats.f_oneway([10.0, 10.2, 10.4], [12.0, 12.2], [15.0, 15.1])
    assert row["n_groups"] == 4
    assert row["F"] == pytest.approx(expected_f)
    assert row["p_value"] == pytest.approx(expected_p)

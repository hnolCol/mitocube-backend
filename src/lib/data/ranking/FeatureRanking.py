
"""
Statistical Metrics for Protein Differential Analysis
====================================================

This module computes statistical and effect-size metrics to identify proteins
that vary significantly across multiple experimental conditions within a submission.

Each metric captures a different aspect of variation:

------------------------------------------------------------
1. F-statistic (ANOVA)
------------------------------------------------------------
- Measures whether there are statistically significant differences between
  group means (conditions).
- High F-value indicates that at least one group differs from others.
- Does NOT indicate magnitude of change, only relative variance.

------------------------------------------------------------
2. p-value
------------------------------------------------------------
- Probability that observed differences occurred by chance.
- Typically, p < 0.05 is considered statistically significant.
- Sensitive to sample size (large datasets may yield small p-values even for small effects).

------------------------------------------------------------
3. Eta Squared (η²)
------------------------------------------------------------
- Effect size representing the proportion of total variance explained by group differences.
- Range: 0 to 1
    0   → no group effect
    1   → all variance explained by group differences
- Interpretation (rule of thumb):
    ~0.01 → small effect
    ~0.06 → medium effect
    ~0.14 → large effect

------------------------------------------------------------
4. Cohen’s f
------------------------------------------------------------
- Standardized effect size derived from η².
- Useful for comparing across experiments.
- Interpretation:
    ~0.10 → small
    ~0.25 → medium
    ~0.40 → large

------------------------------------------------------------
5. Max Pairwise Fold Change (log2 scale)
------------------------------------------------------------
- Maximum absolute difference between any two group means.
- Since values are log2-transformed:
    1   → 2-fold change
    2   → 4-fold change
- Captures the strongest biological signal across conditions.

------------------------------------------------------------
6. Standard Deviation of Group Means
------------------------------------------------------------
- Measures spread of group averages.
- High value indicates strong variability across conditions.
- Less sensitive to outliers than max fold change.

------------------------------------------------------------
7. Missingness
------------------------------------------------------------
- Fraction of missing observations for a protein.
- Range: 0 to 1
    0   → fully observed
    1   → completely missing
- High missingness reduces reliability of statistical estimates.

------------------------------------------------------------
8. Number of Groups (n_groups)
------------------------------------------------------------
- Number of distinct condition groups for the protein.
- More groups increase statistical complexity and robustness.
- Very small group counts reduce reliability of ANOVA.

------------------------------------------------------------
9. Composite Score
------------------------------------------------------------
- Combined metric used to rank proteins by biological relevance.
- Example formula:
    
    score = η² × max_fold_change × log10(n_groups + 1)

- Intuition:
    - η² → consistency of differences
    - max_fold_change → magnitude of change
    - n_groups → diversity of conditions

- High score indicates:
    → strong, consistent, and large differences across conditions

------------------------------------------------------------
Usage Notes
------------------------------------------------------------
- F-statistic and p-value assess statistical significance.
- Effect sizes (η², Cohen’s f, fold change) assess biological relevance.
- Composite score prioritizes proteins for exploration and visualization.
- These metrics are computed per protein within each submission.

------------------------------------------------------------
Caveats
------------------------------------------------------------
- ANOVA assumes roughly normally distributed values and similar variances.
- Missing data can bias results if not handled properly.
- High statistical significance does not always imply biological importance.
- Effect size should always be considered alongside p-values.

------------------------------------------------------------
Recommended Interpretation Strategy
------------------------------------------------------------
1. Filter proteins with:
    - low missingness
    - sufficient number of groups

2. Prioritize proteins with:
    - high η² (strong group effect)
    - high max fold change (biological relevance)

3. Use composite score for ranking datasets and proteins.

"""

import numpy as np 
import pandas as pd 
from scipy import stats


class FeatureRanking(object):
    
    def __init__(self):
        ""
        
    def compute_metrics(self, df : pd.DataFrame) -> pd.DataFrame:
        """Compute metrics for Feature Ranking across submissions. The goal is to use these metrices to rank features across submissions.

        Parameters
        ----------
        df : pd.DataFrame
            DataFrame containing the feature values and group information.
            Expected columns tag (protein_group_tag, value (log2 intensity)) ca_tags List of condition application tags, sample_tag, attribute_tag

        Returns
        -------
        pd.DataFrame
            DataFrame containing the computed metrics for each feature
        """
        ca_annotation_counts = df.dropna(subset=["ca_tags"]).groupby(["attribute_tag", "ca_tags"])["sample_tag"].nunique()
        df_no_nan = df.dropna(subset=["value", "ca_tags"])
        
        total_results = []
        for attribute_tag, df in df_no_nan.groupby("attribute_tag"):

            # A condition application group is only valid if it is annotated on at least two samples.
            # This avoids per-sample attributes (e.g. MouseID) where every sample forms its own group.
            attribute_ca_counts = ca_annotation_counts.xs(attribute_tag, level="attribute_tag")
            valid_ca_tags = attribute_ca_counts[attribute_ca_counts >= 2].index
            n_attribute_groups = len(valid_ca_tags)
            df = df[df["ca_tags"].isin(valid_ca_tags)]
            if df.empty:
                continue

            n_samples = df["sample_tag"].nunique()

            # ---------------------------
            # Group aggregates as protein group x condition application matrices
            # ---------------------------
            grouped = df.groupby(["protein_group_tag", "ca_tags"])["value"]
            group_counts = grouped.size().unstack("ca_tags")
            group_means = grouped.mean().unstack("ca_tags")

            counts = group_counts.fillna(0).to_numpy()
            means = group_means.to_numpy()
            total_counts = counts.sum(axis=1)
            n_groups = (counts > 0).sum(axis=1)
            valid = counts > 0
            grand_means = np.where(valid, np.nan_to_num(means) * counts, 0.0).sum(axis=1) / total_counts

            # ---------------------------
            # Sum of squares
            # ---------------------------
            ss_between = np.where(valid, counts * np.nan_to_num(means - grand_means[:, None])**2, 0.0).sum(axis=1)
            deviations = df["value"] - grouped.transform("mean")
            ss_within = (deviations**2).groupby(df["protein_group_tag"]).sum().reindex(group_counts.index).to_numpy()
            ss_total = ss_between + ss_within

            # ---------------------------
            # Effect sizes
            # ---------------------------
            eta_squared = np.divide(ss_between, ss_total, out=np.zeros_like(ss_between, dtype=float), where=ss_total > 0)
            cohen_f = np.where(eta_squared < 1, np.sqrt(eta_squared / np.clip(1 - eta_squared, 0, None)), np.nan)

            # Max pairwise fold change (log2 already): the largest absolute difference of two group means is the range of the means
            max_fc = np.nanmax(means, axis=1) - np.nanmin(means, axis=1)

            # Std of means
            std_means = np.nanstd(means, axis=1)

            # ---------------------------
            # Exclusivity
            # ---------------------------
            # A protein group is exclusively quantified if it has values in exactly one condition application
            # group and is quantified in at least two samples of that group. ANOVA is not applicable in that case.
            exclusively = (n_groups == 1) & (total_counts > 1)
            exclusively_ca_tags = np.where(exclusively, group_counts.idxmax(axis=1).astype(object), None)

            # ---------------------------
            # ANOVA (one-way, vectorized: F = (ss_between/(k-1)) / (ss_within/(N-k)))
            # ---------------------------
            # Groups with a single observation carry no within-group variance and would inflate the F statistic.
            multi = counts >= 2
            k = multi.sum(axis=1)
            n_anova = np.where(multi, counts, 0).sum(axis=1)
            anova_grand_means = np.where(multi, np.nan_to_num(means) * counts, 0.0).sum(axis=1) / n_anova
            ss_between_anova = np.where(multi, counts * (np.nan_to_num(means) - anova_grand_means[:, None])**2, 0.0).sum(axis=1)
            group_sizes_per_row = grouped.transform("size")
            ss_within_anova = (deviations**2).where(group_sizes_per_row >= 2).groupby(df["protein_group_tag"]).sum().reindex(group_counts.index).to_numpy()

            with np.errstate(divide="ignore", invalid="ignore"):
                f_stat = (ss_between_anova / np.maximum(k - 1, 1)) / (ss_within_anova / np.maximum(n_anova - k, 1))
                p_value = stats.f.sf(f_stat, k - 1, n_anova - k)
            anova_mask = (~exclusively) & (k >= 2) & (n_anova - k > 0)
            finite = anova_mask & np.isfinite(f_stat) & np.isfinite(p_value) #zero within-group variance produces an infinite F statistic
            f_stat = np.where(finite, f_stat, np.nan)
            p_value = np.where(finite, p_value, np.nan)

            # ---------------------------
            # Data quality
            # ---------------------------
            observed = total_counts
            missingness = 1 - (observed / n_samples)

            # ---------------------------
            # Composite score
            # ---------------------------
            # For exclusively quantified protein groups, exclusivity is the maximal group effect:
            # eta_squared and max_fc are treated as 1 so that they rank by the number of alternative
            # groups they are absent from.
            score = np.where(
                exclusively,
                np.log10(n_attribute_groups + 1),
                eta_squared * max_fc * np.log10(n_groups + 1)
            )

            df_attribute = pd.DataFrame({
                "protein_group_tag": group_counts.index,
                "attribute_tag": attribute_tag,
                "score": score,
                "mean": grand_means,
                "quantified_in_samples": observed,
                "F": f_stat,
                "p_value": p_value,
                "eta_squared": eta_squared,
                "cohen_f": cohen_f,
                "max_fc": max_fc,
                "std_means": std_means,
                "missingness": missingness,
                "n_groups": n_groups,
                "exclusively": exclusively,
                "exclusively_ca_tags": [[tag] if tag is not None else [] for tag in exclusively_ca_tags]
            })
            df_attribute.loc[:,"FDR"] = np.nan
            df_attribute.loc[:,"rank"] = df_attribute["score"].rank(ascending=False, method="min").values
            df_no_nan_attribute = df_attribute.dropna(subset=["p_value"])
        
            p_adjusted = stats.false_discovery_control(df_no_nan_attribute["p_value"].values, method="bh")
            df_attribute.loc[df_no_nan_attribute.index, "FDR"] = p_adjusted
            total_results.append(df_attribute)
        if len(total_results) > 1:
            return pd.concat(total_results, ignore_index=True)
        elif len(total_results) == 1:
            return total_results[0]
        print(total_results)
        print("No valid data to compute metrics. Returning empty DataFrame.")
        return pd.DataFrame()
        
    

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
from itertools import combinations


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
        
        df_no_nan = df.dropna(subset=["value", "ca_tags"])
        total_results = []
        for attribute_tag, df in df_no_nan.groupby("attribute_tag"):
        
            results = []
            df_pivot_mean = pd.pivot_table(df, index="protein_group_tag", columns="ca_tags", values="value", aggfunc="mean")
            df_pivot_count = pd.pivot_table(df, index="protein_group_tag", columns="ca_tags", values="value", aggfunc="count")
            df_grouped_values = df.groupby(["protein_group_tag","ca_tags"])["value"].apply(list)
            

            for protein_group_tag, pdf in df.groupby("protein_group_tag"):
                exclusively = False
                exclusively_ca_tags = []
                f_stat, p_value = np.nan, np.nan
                # Drop missing
                pdf = pdf.dropna(subset=["value", "ca_tags"])

                groups = pdf.groupby("ca_tags")["value"].apply(list)

                # ---------------------------
                # Basic stats
                # ---------------------------
                group_means = {g: df_pivot_mean.loc[protein_group_tag, g] for g in groups.keys()}
                group_sizes = {g: df_pivot_count.loc[protein_group_tag, g] for g in groups.keys()}
                
                all_values = pdf["value"].values
                grand_mean = np.mean(all_values)

                # ---------------------------
                # ANOVA
                # ---------------------------
                sizes = group_sizes.values() 
                bools_group_size_not_null = [s > 0 for s in sizes]
                bools_group_size_at_least_2 = [s >= 2 for s in sizes]
                group_sizes_not_null_sum = sum(bools_group_size_not_null)
                exclusively = group_sizes_not_null_sum == 1 and sum(sizes) > 1 #if only one group has non-null size and that size is > 4, we consider the protein exclusively present in that group. In this case, ANOVA is not applicable, but we can still compute effect sizes.
                if exclusively:
                    exclusively_ca_tags = [g for g, s in group_sizes.items() if s > 0]
                
                if not exclusively and group_sizes_not_null_sum > 1 and sum(bools_group_size_at_least_2) >= 2: #ANOVA requires at least 2 groups with non-null size
                    try:
                        f_stat, p_value = stats.f_oneway(*df_grouped_values.loc[protein_group_tag].values)
                    except Exception:
                        pass 
        
                # group means and counts as arrays
                means = np.array([group_means[g] for g in groups.keys()])
                counts = np.array([group_sizes[g] for g in groups.keys()])

                # ss_between
                ss_between = np.sum(counts * (means - grand_mean)**2)
                # ---------------------------
                # Sum of squares
                # ---------------------------
                # ss_between = sum(
                #     group_sizes[g] * (group_means[g] - grand_mean) ** 2
                #     for g in groups.keys()
                # )

                ss_within = np.sum([
                    np.sum((np.array(values) - df_pivot_mean.loc[protein_group_tag, g])**2)
                    for g, values in groups.items()
                ])

                ss_total = ss_between + ss_within

                # ---------------------------
                # Effect sizes
                # ---------------------------
                eta_squared = ss_between / ss_total if ss_total > 0 else 0

                cohen_f = np.sqrt(eta_squared / (1 - eta_squared)) if eta_squared < 1 else np.inf

                # Max pairwise fold change (log2 already)
                max_fc = 0
                for g1, g2 in combinations(group_means.keys(), 2):
                    fc = abs(group_means[g1] - group_means[g2])
                    max_fc = max(max_fc, fc)

                # Std of means
                std_means = np.std(list(group_means.values()))

                # ---------------------------
                # Data quality
                # ---------------------------
                total_expected = len(pdf["sample_tag"].unique())
                observed = len(pdf)
                missingness = 1 - (observed / total_expected)

                n_groups = len(groups)

                # ---------------------------
                # Composite score
                # ---------------------------
                score = eta_squared * max_fc * np.log10(n_groups + 1)

                results.append({
                    "protein_group_tag": protein_group_tag,
                    "attribute_tag": attribute_tag,
                    "score": score,
                    "mean": np.mean(all_values),
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
                    "exclusively_ca_tags": exclusively_ca_tags
                })
            df_attribute = pd.DataFrame(results)
            df_attribute.loc[:,"FDR"] = np.nan
            df_attribute.loc[:,"rank"] = df_attribute["score"].rank(ascending=False, method="min").values
            df_no_nan_attribute = df_attribute.dropna(subset=["p_value"])
            p_adjusted = stats.false_discovery_control(df_no_nan_attribute["p_value"].values, method="bh")
            df_attribute.loc[df_no_nan_attribute.index, "FDR"] = p_adjusted[1]
            total_results.append(df_attribute)
        df = pd.concat(total_results, ignore_index=True)
            
        #df.loc[:,"FDR"] = df.groupby("attribute_tag")["p_value"].transform(lambda p: stats.false_discovery_control(p, method="fdr_bh")[1])
        #df.loc[:"rank"] = df.groupby("attribute_tag")["score"].rank(ascending=False, method="min")
        return df

        
    
from dataclasses import dataclass

import pandas as pd
from typing import Optional,List, Dict, Literal
import os

from services.random_generators import get_random_string
from services.encryption import create_hierarchical_hash
from neo4j import Driver, Result

from collections import defaultdict
from services.json import read_json

from config.models.annotations.annotations import ( AnnotationGroupsModel, AnnotationsModel )
from lib.database.abstract.Annotations import ( AnnotationGroupsABC, AnnotationsABC )
from scipy.stats import mannwhitneyu



def _benjamini_hochberg(p_values: pd.Series) -> pd.Series:
    """Manual BH FDR correction (avoids a statsmodels dependency)."""
    p = p_values.to_numpy(dtype=float)
    n = len(p)
    if n == 0:
        return pd.Series([], dtype=float, index=p_values.index)

    order = p.argsort()
    ranked = p[order]
    ranks = pd.Series(range(1, n + 1))
    bh = ranked * n / ranks.to_numpy()

    bh_sorted_back = pd.Series(bh).iloc[::-1].cummin().iloc[::-1].to_numpy()
    bh_sorted_back = bh_sorted_back.clip(max=1.0)

    out = pd.Series(index=p_values.index, dtype=float)
    out.iloc[order] = bh_sorted_back
    return out


@dataclass
class AnnotationVarianceResult:
    table: pd.DataFrame

    def top(self, n: int = 20, fdr_threshold: float = 0.05) -> pd.DataFrame:
        if self.table.empty:
            return self.table
        sig = self.table[self.table["FDR"] <= fdr_threshold]
        return sig.sort_values("p_value").head(n)

def _run_mannwhitney_enrichment(
    df: pd.DataFrame,
    background_scope: Literal["global", "within_parent_group"],
    effect_field: Literal["eta_squared", "cohen_f", "neg_log10_p"],
    min_group_size: int,
    fdr_scope: Literal["per_submission", "global"],
    alternative: Literal["greater", "less", "two-sided"]) -> AnnotationVarianceResult:

    """
    Statistical core. `df` must have one row per (submission_tag,
    protein_group_tag) with a `memberships` column: a list of
    {"group_tag": ..., "parent_group_tag": ... or None} dicts (as
    produced by either Cypher query above via Result.to_df).
    """
    work = df.copy()

    if effect_field == "neg_log10_p":
        import numpy as np
        eps = work["p_value"].replace(0, pd.NA).dropna()
        floor = eps.min() / 10 if not eps.empty else 1e-300
        work["neg_log10_p"] = -np.log10(work["p_value"].clip(lower=floor))

    work = work.dropna(subset=[effect_field])

    # one row per (submission, protein_group), no duplication -- this is
    # the universe of "everything tested" for global background lookups.
    base = work[["submission_tag", "protein_group_tag", effect_field]].drop_duplicates(
        subset=["submission_tag", "protein_group_tag"]
    )

    # explode memberships: one row per (submission, protein_group, group_tag)
    exploded = work.explode("memberships")
    exploded = exploded.dropna(subset=["memberships"])
    exploded["group_tag"] = exploded["memberships"].apply(lambda m: m["group_tag"])
    exploded["parent_group_tag"] = exploded["memberships"].apply(lambda m: m.get("parent_group_tag"))
    exploded = exploded.dropna(subset=["group_tag"])

    rows = []
    for (submission_tag, group_tag), grp in exploded.groupby(
        ["submission_tag", "group_tag"]
    ):
        in_group_pgs = set(grp["protein_group_tag"])
        parent_group_tag = grp["parent_group_tag"].iloc[0]  # constant within a group_tag

        if background_scope == "within_parent_group" and pd.notna(parent_group_tag):
            # siblings: other protein groups under the SAME parent
            # AnnotationGroup, excluding members of this Annotation.
            sibling_mask = (
                (exploded["submission_tag"] == submission_tag)
                & (exploded["parent_group_tag"] == parent_group_tag)
            )
            candidate_pool = exploded[sibling_mask][
                ["protein_group_tag", effect_field]
            ].drop_duplicates(subset=["protein_group_tag"])
        else:
            # global: everything else tested in the submission
            candidate_pool = base[base["submission_tag"] == submission_tag]

        in_vals = candidate_pool[
            candidate_pool["protein_group_tag"].isin(in_group_pgs)
        ][effect_field].to_numpy()
        out_vals = candidate_pool[
            ~candidate_pool["protein_group_tag"].isin(in_group_pgs)
        ][effect_field].to_numpy()

        if len(in_vals) < min_group_size or len(out_vals) < min_group_size:
            continue

        try:
            U, p = mannwhitneyu(in_vals, out_vals, alternative=alternative)
        except ValueError:
            continue

        rows.append(
            {
                "submission_tag": submission_tag,
                "group_tag": group_tag,
                "parent_group_tag": parent_group_tag,
                "n_in": len(in_vals),
                "n_out": len(out_vals),
                "median_in": pd.Series(in_vals).median(),
                "median_out": pd.Series(out_vals).median(),
                "mean_in": pd.Series(in_vals).mean(),
                "mean_out": pd.Series(out_vals).mean(),
                "U_statistic": U,
                "p_value": p,
                "direction": "elevated" if pd.Series(in_vals).median()
                >= pd.Series(out_vals).median() else "reduced",
            }
        )

    result = pd.DataFrame(rows)
    if result.empty:
        return AnnotationVarianceResult(result)

    if fdr_scope == "global":
        result["FDR"] = _benjamini_hochberg(result["p_value"])
    else:
        result["FDR"] = result.groupby("submission_tag")["p_value"].transform(
            _benjamini_hochberg
        )

    result = result.sort_values(["submission_tag", "p_value"]).reset_index(drop=True)
    
    return AnnotationVarianceResult(result)


class Neo4JAnnotationGroups(AnnotationGroupsABC):

    def __init__(self, driver : Driver) -> None:
        self._driver = driver

    def exists(self, tag: str) -> bool:
        """Checks if an annoation groupt exists."""

        query = (
            "WITH EXISTS {(ag:AnnotationGroup {tag: $group_tag})} AS ag_exists "
            "RETURN ag_exists "
        )

        r = self._driver.execute_query(query, group_tag=tag, result_transformer_=Result.value)
        return r[0]


    def insert(self, annotationgroup: AnnotationGroupsModel, user_tag: str ) -> bool:
        """Creates a new annnotation group."""

        query = (
           "MATCH (u:User {tag: $user_tag}) "
           "MERGE (ag:AnnotationGroup {tag: $tag}) "
            "ON CREATE "
            "SET ag.text = $text, "
            "    ag.description = $description, "
            "    ag.source = $source, "
            "    ag.url = $url, "
            "    ag.created_at = timestamp(), "
            "    ag.created_by = u.tag "
            "RETURN TRUE"
        )

        r = self._driver.execute_query( query,
                                        user_tag=user_tag,
                                        tag=annotationgroup.tag,
                                        text=annotationgroup.text,
                                        description=annotationgroup.description,
                                        source=annotationgroup.source,
                                        url=annotationgroup.url,
                                        routing_="w",
                                        result_transformer_=Result.value,
                                    )
        
        return r[0] if r else False
    
    def get(self, tag: str) -> AnnotationGroupsModel:
       
        query = (
            "MATCH (ag:AnnotationGroup {tag: $tag}) "
            "RETURN properties(ag)"
        )

        r = self._driver.execute_query( query,
                                        tag=tag,
                                        routing_="r",
                                        result_transformer_=Result.value,
                                    )

        return AnnotationGroupsModel(**r[0])

    
    def find( self, search_string: Optional[str] = None,  protein_tag: Optional[str] = None, search_in_annotations : bool = False, return_annotations : bool = False, submission_tags : Optional[List[str]] = None, limit : int = None) -> List[str]:

        query = "MATCH (ag:AnnotationGroup) "

        where_clauses = []

        # Protein filter
        if protein_tag:
            where_clauses.append("""
            EXISTS {
                MATCH (ag)-[:HAS_ANNOTATION]->(:Annotation)-[:ANNOTATES]->
                    (:Protein {tag: $protein_tag})
            }
            """)

        # Submission filter
        if submission_tags:
            where_clauses.append("""
            EXISTS {
                MATCH (ag)-[:HAS_ANNOTATION]->(:Annotation)-[:ANNOTATES]->(p:Protein)
                    <-[:HAS_PROTEINS]-(pg:ProteinGroup)
                    <-[:QUANTIFIED]-(:Sample)
                    <-[:HAS_SAMPLE]-(submission:Submission)
                WHERE submission.tag IN $submission_tags
            }
            """)

        # Search filter
        if search_string:

            if not search_in_annotations:

                where_clauses.append("""
                (
                    toLower(ag.text) CONTAINS toLower($search_string)
                    OR toLower(ag.description) CONTAINS toLower($search_string)
                )
                """)

            else:

                where_clauses.append("""
                (
                    toLower(ag.text) CONTAINS toLower($search_string)
                    OR toLower(ag.description) CONTAINS toLower($search_string)

                    OR EXISTS {
                        MATCH (ag)-[:HAS_ANNOTATION]->(a:Annotation)
                        WHERE
                            toLower(a.text) CONTAINS toLower($search_string)
                            OR toLower(a.description) CONTAINS toLower($search_string)
                    }
                )
                """)

        # Assemble WHERE
        if where_clauses:
            query += "WHERE " + " AND ".join(where_clauses) + " "

        # Optional annotation expansion only when needed
        if return_annotations:

            query += """
            OPTIONAL MATCH (ag)-[:HAS_ANNOTATION]->(a:Annotation)

            RETURN {
                group_tag: ag.tag,
                annotation_tags: collect(DISTINCT a.tag)
            } AS result
            """

        else:

            query += "RETURN ag.tag AS tag "

        if limit is not None:
            query += "LIMIT $limit"

        r = self._driver.execute_query( query,
                                        search_string=search_string,
                                        protein_tag=protein_tag,
                                        submission_tags=submission_tags,
                                        routing_="r",
                                        result_transformer_=Result.value,
                                    )
        
        return r
    
    def get_annotations(self, group_tag: str, limit: int = 20) -> List[str]:

        query = (
            "MATCH (:AnnotationGroup {tag: $tag})-[:HAS_ANNOTATION]->(a:Annotation) "
            "RETURN a.tag "
            "LIMIT $limit "
        )

        r = self._driver.execute_query( query,
                                        tag=group_tag,
                                        limit=limit,
                                        routing_="r",
                                        result_transformer_=Result.value,
                                    )
        
        return r

    def count_annotations(self, group_tag: str) -> int:
        
        query = (
            "MATCH (:AnnotationGroup {tag: $tag})-[:HAS_ANNOTATION]->(a:Annotation) "
            "RETURN count(a)"
        )
        r = self._driver.execute_query( query,
                                        tag=group_tag,
                                        routing_="r",
                                        result_transformer_=Result.value,
                                    )

        return r[0] if r else 0
    
    def edit_annotation_group(self, annotationgroup: AnnotationGroupsModel, user_tag: str) -> bool:
        """Updates an existing annotation group."""

        query = (
            "MATCH (ag:AnnotationGroup {tag: $tag}) "
            "SET "
            " ag.text = $text, "
            " ag.description = $description, "
            " ag.source = $source, "
            " ag.url = $url, "
            " ag.modified_at = timestamp() "
            "WITH ag "
            "MATCH (u:User {tag: $user_tag}) "
            "CREATE (u)-[:MODIFIED {modified_at: timestamp()}]->(ag) "
            "RETURN TRUE "
        )

        r = self._driver.execute_query( query,
                                        tag=annotationgroup.tag,
                                        text=annotationgroup.text,
                                        description=annotationgroup.description,
                                        source=annotationgroup.source,
                                        url=annotationgroup.url,
                                        user_tag=user_tag,
                                        routing_="w",
                                        result_transformer_=Result.value,
                                    )
        
        return r[0] if r else False


    def test_variance_enrichment(
        self,
        attribute_tag: str,
        submission_tags: Optional[List[str]] = None,
        level: Literal["annotation_group", "annotation"] = "annotation",
        background_scope: Literal["global", "within_parent_group"] = "global",
        effect_field: Literal["eta_squared", "cohen_f", "neg_log10_p"] = "eta_squared",
        min_group_size: int = 3,
        fdr_scope: Literal["per_submission", "global"] = "per_submission",
        alternative: Literal["greater", "less", "two-sided"] = "greater",
        annotation_tags : Optional[List[str]] = None,
        annotation_group_tags : Optional[List[str]] = None,
    ) -> AnnotationVarianceResult:
        """
        Tests, per submission, whether any AnnotationGroup (or, if
        level="annotation", any individual Annotation) shows higher (or
        lower, if alternative != "greater") `effect_field` from the
        precomputed Statistic node than its background. Uses a one-sided
        Mann-Whitney U test with Benjamini-Hochberg FDR correction.
    
        Parameters
        ----------
        attribute_tag : str
            Must match Statistic.attribute_tag (e.g. "treatment", "genotype").
        submission_tags : list[str] or None
            Restrict to these submissions. None = all submissions that have
            Statistic nodes for this attribute_tag.
        level : "annotation_group" | "annotation"
            Granularity to test. "annotation_group" tests whole groups (e.g.
            gene sets). "annotation" tests individual terms within those
            groups.
        background_scope : "global" | "within_parent_group"
            Only used when level="annotation". "global": background is
            every other tested ProteinGroup in the submission.
            "within_parent_group": background is restricted to other
            ProteinGroups belonging to the same parent AnnotationGroup,
            excluding this Annotation -- i.e. "does this term stand out
            from its siblings", not "...from the whole proteome". Ignored
            (treated as "global") when level="annotation_group", since a
            group has no parent to scope against.
        effect_field : "eta_squared" | "cohen_f" | "neg_log10_p"
            Which Statistic field to test for enrichment.
        min_group_size : int
            Skip (submission, group) pairs with fewer than this many
            quantified protein groups on either side of the test.
        fdr_scope : "per_submission" | "global"
            BH correction scope: within each submission's tested groups, or
            once across the whole output table.
        alternative : "greater" | "less" | "two-sided"
            "greater" (default): tests for groups MORE affected than
            background. "two-sided" also catches unusually stable groups.
    
        Returns
        -------
        AnnotationVarianceResult wrapping a DataFrame with columns:
            submission_tag, group_tag, parent_group_tag (None at
            annotation_group level), n_in, n_out, median_in, median_out,
            mean_in, mean_out, U_statistic, p_value, FDR, direction
        """
        if level == "annotation_group":
            query = (
                "MATCH (attribute:Attribute)<-[:OF_ATTRIBUTE]-(s:Statistics)-[:FOR_PROTEIN_GROUP]->(pg:ProteinGroup) WHERE attribute.tag = $attribute_tag "
                "MATCH (s)-[:HAS_STATS]-(submission:Submission) "
                "WHERE ($submission_tags IS NULL OR submission.tag IN $submission_tags) "
                "OPTIONAL MATCH (pg)-[:HAS_PROTEINS]->(p:Protein)<-[:ANNOTATES]-(a:Annotation)<-[:HAS_ANNOTATION]-(ag:AnnotationGroup) "
                "WHERE ($annotation_group_tags IS NULL OR ag.tag IN $annotation_group_tags) "
                "RETURN "
                " submission.tag AS submission_tag, "
                " pg.tag AS protein_group_tag, "
                " s.eta_squared AS eta_squared, "
                " s.cohen_f AS cohen_f, "
                " s.p_value AS p_value, "
                " collect({group_tag: ag.tag, parent_group_tag: null}) AS memberships "
            )
        else:  # level == "annotation"
            query = (
                "MATCH (attribute:Attribute)<-[:OF_ATTRIBUTE]-(s:Statistics)-[:FOR_PROTEIN_GROUP]->(pg:ProteinGroup) WHERE attribute.tag = $attribute_tag "
                "MATCH (s)<-[:HAS_STATS]-(submission:Submission) "
                "WHERE ($submission_tags IS NULL OR submission.tag IN $submission_tags) "
                "OPTIONAL MATCH (pg)-[:HAS_PROTEINS]->(p:Protein)<-[:ANNOTATES]-(a:Annotation)<-[:HAS_ANNOTATION]-(ag:AnnotationGroup) "
                "WHERE ($annotation_tags IS NULL OR a.tag IN $annotation_tags) "
                "RETURN "
                " submission.tag AS submission_tag, "
                " pg.tag AS protein_group_tag, "
                " s.eta_squared AS eta_squared, "
                " s.cohen_f AS cohen_f, "
                " s.p_value AS p_value, "
                " collect({group_tag: a.tag, parent_group_tag: ag.tag}) AS memberships "
            )
    
        df = self._driver.execute_query(
            query,
            attribute_tag=attribute_tag,
            submission_tags=submission_tags,
            annotation_tags=annotation_tags,
            annotation_group_tags=annotation_group_tags,
            routing_="r",
            result_transformer_=Result.to_df,
        )
        
        if df.empty:
            return AnnotationVarianceResult(df)
    
        return _run_mannwhitney_enrichment(
            df,
            background_scope=background_scope if level == "annotation" else "global",
            effect_field=effect_field,
            min_group_size=min_group_size,
            fdr_scope=fdr_scope,
            alternative=alternative,
        )
    


class Neo4JAnnotations(AnnotationsABC):

    def __init__(self, driver: Driver) -> None:
        self._driver = driver

    def _utils_insert_from_file(self, user_tag: str, file_path: str, folder_path: str = "") -> None:
        """Inserts annotations from a config JSON file.
        Supports multiple groups, each with multiple annotation entries.
        Each annotation entry can be:
        - Grouped by column: { "file_path": "...", "annotation_text_column": "...", "protein_tag_column": "..." }
        - Fixed text: { "text": "...", "file_path": "...", "protein_tag_column": "..." }
        Optional per entry:
        - "protein_delimiter": ";" — splits multi-protein cells
        - "reviewed_filter": true — for multi-protein cells, keeps only proteins that are reviewed in the DB
        """
# The code is attempting to print the value of the variable `user_tag`, but it seems that the variable
# `user_tag` is not defined in the provided code snippet.
        config = read_json(file_path)

        if "groups" not in config:
            raise ValueError("JSON file must have a 'groups' key.")


        for group_config in config["groups"]:
            ag = group_config["annotation_group"]
            group_tag = create_hierarchical_hash(ag)
            # Create annotation group
            #group_tag = get_random_string(5)
            query = (
                "MATCH (u:User {tag: $user_tag}) "
                "MERGE (ag:AnnotationGroup {tag: $tag}) "
                "ON CREATE "
                "SET ag.text = $text, "
                "    ag.description = $description, "
                "    ag.source = $source, "
                "    ag.created_at = timestamp(), "
                "    ag.created_by = u.tag "
                "ON MATCH "
                "SET ag.text = $text, "
                "    ag.description = $description, "
                "    ag.source = $source, "
                "    ag.modified_at = timestamp(), "
                "    ag.modified_by = u.tag "
                "RETURN ag.tag "
            )
            r = self._driver.execute_query(
                query,
                tag=group_tag,
                text=ag["text"],
                description=ag.get("description", ""),
                source=ag.get("source", ""),
                user_tag=user_tag,
                routing_="w",
                result_transformer_=Result.value,
            )
    
            print(r, user_tag)
            print(f"  Annotation group '{ag['text']}' ({group_tag}) ready.")

            for entry in group_config["annotations"]:
                data_path = os.path.join(folder_path, entry["file_path"])
                protein_col = entry["protein_tag_column"]
                sheet_name = entry.get("sheet_name", None)
                protein_delimiter = entry.get("protein_delimiter", None)
                reviewed_filter = entry.get("reviewed_filter", False)

                # Read data file
                encoding = entry.get("encoding", "utf-8")
                header = entry.get("header", 0)
                if data_path.endswith(".csv"):
                    df = pd.read_csv(data_path, encoding=encoding, header=header)
                elif data_path.endswith(".tsv") or data_path.endswith(".txt"):
                    df = pd.read_csv(data_path, sep="\t", encoding=encoding, header=header)
                elif data_path.endswith(".xlsx") or data_path.endswith(".xls"):
                    df = pd.read_excel(data_path, sheet_name=sheet_name, header=header)
                else:
                    raise TypeError(f"File type not supported: {data_path}")

                # Flatten multi-level columns if needed
                if isinstance(df.columns, pd.MultiIndex):
                    functional_header = entry.get("functional_header", None)
                    if functional_header:
                        # Forward-fill the top-level headers (handles merged cells)
                        top_level = [col[0] if col[0] and not str(col[0]).startswith('Unnamed') else None for col in df.columns]
                        filled_top = pd.Series(top_level).ffill().tolist()
                        
                        # Get all columns where filled top-level matches functional_header
                        functional_cols = [df.columns[i][1] for i, header in enumerate(filled_top) if header == functional_header]
                    # Flatten column names
                    df.columns = [col[1] if isinstance(col, tuple) else col for col in df.columns]
                else:
                    functional_cols = None

                # Pre-fetch existing proteins if we need to filter
                existing_proteins = set()
                if protein_delimiter and reviewed_filter:
                    all_tags = set()
                    for _, row in df.iterrows():
                        val = row.get(protein_col)
                        if pd.isna(val):
                            continue
                        for t in str(val).split(protein_delimiter):
                            t = t.strip()
                            if t:
                                all_tags.add(t)
                    query = (
                            "UNWIND $tags AS tag "
                            "MATCH (p:Protein {tag: tag}) "
                            "WHERE p.reviewed = true "
                            "RETURN p.tag"
                        )
                    r = self._driver.execute_query(
                        query,
                        tags=list(all_tags),
                        routing_="r",
                        result_transformer_=Result.value,
                    )
                    existing_proteins = set(r)
                    print(f"    Found {len(existing_proteins)} existing proteins out of {len(all_tags)} total")

                def resolve_proteins(value):
                    if pd.isna(value):
                        return []
                    value = str(value).strip()
                    if protein_delimiter and protein_delimiter in value:
                        tags = [t.strip() for t in value.split(protein_delimiter) if t.strip()]
                        if reviewed_filter:
                            reviewed = [t for t in tags if t in existing_proteins]
                            return reviewed if reviewed else [tags[0]]
                        return tags
                    else:
                        return [value] if value else []

                # Check if this is functional column mode
                if functional_cols:
                    annotation_to_proteins = defaultdict(list)
                    for _, row in df.iterrows():
                        proteins = resolve_proteins(row.get(protein_col))
                        if not proteins:
                            continue
                        
                        # Check each functional column
                        for func_col in functional_cols:
                            if row.get(func_col) == 1:
                                annotation_to_proteins[func_col].extend(proteins)

                    for ann_text, proteins in annotation_to_proteins.items():
                        annotation = AnnotationsModel(
                            text=ann_text,
                            description=ann_text,
                            group_tag=group_tag,
                            protein_tags=list(set(proteins)),  # deduplicate
                            source=ag.get("source", ""),
                        )
                        self.insert(annotation=annotation)
                        print(f"    Inserted '{ann_text}' with {len(set(proteins))} proteins")

                elif "annotation_text_column" in entry:
                    annotation_col = entry["annotation_text_column"]
                    annotation_delimiter = entry.get("annotation_delimiter", None)
                    annotation_to_proteins = defaultdict(list)
                    
                    for _, row in df.iterrows():
                        proteins = resolve_proteins(row.get(protein_col))
                        if not proteins:
                            continue
                        
                        ann_texts = row.get(annotation_col)
                        if pd.isna(ann_texts):
                            continue
                        
                        # Split annotation texts if delimiter provided
                        if annotation_delimiter and annotation_delimiter in str(ann_texts):
                            ann_text_list = [t.strip() for t in str(ann_texts).split(annotation_delimiter) if t.strip()]
                        else:
                            ann_text_list = [str(ann_texts).strip()]
                        
                        for ann_text in ann_text_list:
                            annotation_to_proteins[ann_text].extend(proteins)

                    for ann_text, proteins in annotation_to_proteins.items():
                        annotation = AnnotationsModel(
                            text=ann_text,
                            description=ann_text,
                            group_tag=group_tag,
                            protein_tags=proteins,
                            source=ag.get("source", ""),
                        )
                        self.insert(annotation=annotation)
                        print(f"    Inserted '{ann_text}' with {len(proteins)} proteins")

                else:
                    all_proteins = []
                    for _, row in df.iterrows():
                        all_proteins.extend(resolve_proteins(row.get(protein_col)))
                    proteins = list(dict.fromkeys(all_proteins))
                    annotation = AnnotationsModel(
                        text=entry["text"],
                        description=entry.get("description", entry["text"]),
                        group_tag=group_tag,
                        protein_tags=proteins,
                        source=ag.get("source", ""),
                    )
                    self.insert(annotation=annotation)
                    print(f" Inserted '{entry['text']}' with {len(proteins)} proteins")

            print(f"  Done.")

    def count(self) -> int:
        """Counts the total number of annotations in the database."""

        query = (
            "MATCH (a:Annotation) "
            "RETURN count(a)"
        )
        r = self._driver.execute_query( query,
                                        routing_="r",
                                        result_transformer_=Result.value,
                                    )

        return r[0] if r else 0


    def exists(self, tag: str) -> bool:

        query = (
            "WITH EXISTS {(a:Annotation {tag: $tag})} AS a_exists "
            "RETURN a_exists "
        )

        r = self._driver.execute_query( query,
                                        tag=tag,
                                        routing_="r",
                                        result_transformer_=Result.value,
                                    )
        
        return r[0] if r else False




    def insert(self, annotation: AnnotationsModel) -> bool:
       
        query = (
            "MATCH (ag:AnnotationGroup {tag: $group_tag}) "
            "OPTIONAL MATCH (existing:Annotation {tag: $tag}) "
            "WITH ag, existing "
            "WHERE existing IS NULL "
            "CREATE (a:Annotation { "
            " tag: $tag, "
            " text: $text, "
            " description: $description, "
            " publication: $publication, "
            " source: $source, "
            " pubmed_id: $pubmed_id, "
            " s: toLower($text)+' '+toLower(coalesce($description,'')), "
            " created_at: timestamp() "
            "}) "
            "MERGE (ag)-[:HAS_ANNOTATION]->(a) "
            "WITH a "
            "UNWIND $protein_tags AS protein_tag "
            "MATCH (p:Protein {tag: protein_tag}) "
            "MERGE (a)-[:ANNOTATES]->(p) "
            "RETURN TRUE"
        )

        r = self._driver.execute_query(query,
                                        tag=annotation.tag,
                                        text=annotation.text,
                                        description=annotation.description,
                                        publication=annotation.publication,
                                        pubmed_id=annotation.pubmed_id,
                                        source=annotation.source,
                                        protein_tags=annotation.protein_tags or [],
                                        group_tag=annotation.group_tag,
                                        routing_="w",
                                        result_transformer_=Result.value,
                                    )

        if annotation.submission_tags:
            submission_query = (
                "MATCH (a:Annotation {tag: $tag}) "
                "UNWIND $submission_tags AS sub_tag "
                "MATCH (s:Submission {tag: sub_tag}) "
                "MERGE (a)-[:BASED_ON]->(s) "
                "RETURN TRUE"
            )
            self._driver.execute_query(submission_query,
                                        tag=annotation.tag,
                                        submission_tags=annotation.submission_tags,
                                        routing_="w",
                                        result_transformer_=Result.value,
                                    )

        return r[0] if r else False

    def get(self, tag: str) -> AnnotationsModel:

        query = (
            "MATCH (ag:AnnotationGroup)-[:HAS_ANNOTATION]->(a:Annotation {tag: $tag}) "
            "OPTIONAL MATCH (a)-[:ANNOTATES]->(p:Protein) "
            "OPTIONAL MATCH (a)-[:BASED_ON]->(s:Submission) "   
            "RETURN "
            " properties(a) AS a_props, "
            " ag.tag AS group_tag, "
            " collect(DISTINCT p.tag) AS protein_tags, "
            " collect(DISTINCT s.tag) AS submission_tags "       
        )
        r = self._driver.execute_query(query,
                                        tag=tag,
                                        routing_="r",
                                        result_transformer_=Result.data,
                                    )
                                    
        if not r:
            raise Exception("Annotation not found")
        data = r[0]["a_props"]
        data["group_tag"] = r[0]["group_tag"]
        data["protein_tags"] = r[0]["protein_tags"]
        data["submission_tags"] = r[0]["submission_tags"]   
        
        return AnnotationsModel(**data)

    def find(self, search_string: Optional[str] = None, group_tags: Optional[List[str]] = None,  protein_tags: Optional[List[str]] = None, submission_tags: Optional[List[str]] = None, limit: Optional[int] = None, group_by_group = False) -> List[str]:

        where_clauses = []
        query = (
                "MATCH (ag:AnnotationGroup)-[:HAS_ANNOTATION]->(a:Annotation) "
            )
        
        
        if group_tags is not None:
            query += "WHERE ag.tag IN $group_tags "
                
        if submission_tags is not None:
            where_clauses.append("""EXISTS {
                (a)-[:ANNOTATES]->(:Protein)<-[:HAS_PROTEINS]-(pg:ProteinGroup)<-[:QUANTIFIED]-(:Sample)<-[:HAS_SAMPLE]-(s:Submission)
                WHERE s.tag IN $submission_tags
            }""")
        if protein_tags is not None:
            where_clauses.append("EXISTS {(a)-[:ANNOTATES]->(p:Protein) WHERE p.tag in $protein_tags} ")
                

        if search_string is not None and search_string != "":

            where_clauses.append("toLower(a.text) CONTAINS $search_string ")
        
        query += "WHERE " + " AND ".join(where_clauses) + " " if where_clauses else ""
        if group_by_group:
            query += "RETURN ag.tag, a.tag "
        else: 
            query += "RETURN a.tag "
        
        if limit is not None:
            query += "LIMIT $limit"
        
        print(query, search_string, group_tags, protein_tags, submission_tags, limit)
        r = self._driver.execute_query( query,
                                        group_tags=group_tags,
                                        protein_tags=protein_tags,
                                        limit=limit,
                                        submission_tags=submission_tags,
                                        search_string=search_string.strip().lower() if search_string else None,
                                        routing_="r",
                                        result_transformer_=Result.values,
                                    )
        if group_by_group:
            grouped = {}
            for group_tag, annotation_tag in r:
                if group_tag not in grouped:
                    grouped[group_tag] = []
                grouped[group_tag].append(annotation_tag)
            return [ {"group_tag": k, "annotation_tags": i} for k,i in grouped.items()]
        return r

    def count_proteins(self, tag: str) -> int:

        query = (
            "MATCH (:Annotation {tag: $tag})-[:ANNOTATES]->(p:Protein) "
            "RETURN count(p)"
        )

        r = self._driver.execute_query( query,
                                        tag=tag,
                                        routing_="r",
                                        result_transformer_=Result.value,
                                    )

        return r[0] if r else 0

    def get_protein_tags(self, tag: str, submission_tag: Optional[str] = None) -> List[str]:
        """Get proteins for annotation, optionally filtered by submission."""
        
        if submission_tag:
            query = (
                "MATCH (s:Submission {tag: $submission_tag})-[:HAS_SAMPLE]->(:Sample)-[:QUANTIFIED]->(pg:ProteinGroup)-[:HAS_PROTEINS]->(p:Protein) "
                "MATCH (:Annotation {tag: $tag})-[:ANNOTATES]->(p) "
                "RETURN DISTINCT p.tag"
            )
            r = self._driver.execute_query(
                query,
                tag=tag,
                submission_tag=submission_tag,
                routing_="r",
                result_transformer_=Result.value,
            )
        else:
            query = (
                "MATCH (:Annotation {tag: $tag})-[:ANNOTATES]->(p:Protein) "
                "RETURN p.tag"
            )
            r = self._driver.execute_query(
                query,
                tag=tag,
                routing_="r",
                result_transformer_=Result.value,
            )
        
        return r
    
    def get_text(self, tag: str) -> str:
        query = "MATCH (a:Annotation {tag: $tag}) RETURN a.text AS text"
        result = self._driver.execute_query(
            query,
            tag=tag,
            result_transformer_=lambda r: r.single()
        )
        return result["text"] if result else None
    
    def isin(self, tag: str, protein_tags: List[str]) -> pd.Series:

        query = (
            "MATCH (p:Protein) "
            "WHERE p.tag IN $protein_tags "
            "RETURN p.tag AS tag, "
            "EXISTS {(:Annotation {tag: $tag})-[:ANNOTATES]->(p)} AS isin"
        )
        r = self._driver.execute_query( query,
                                        protein_tags=protein_tags,
                                        tag=tag,
                                        routing_="r",
                                        result_transformer_=Result.to_df,
                                    )
        
        if r.empty:
            return pd.Series([], dtype=bool)
        
        r = r.set_index("tag")

        return r["isin"]

    def count_proteins(self, tag: str) -> int:
        
        query = (
            "MATCH (a:Annotation {tag: $tag})-[:ANNOTATES]->(p:Protein) "
            "RETURN count(p)"
        )

        r = self._driver.execute_query( query,
                                        tag=tag,
                                        routing_="r",
                                        result_transformer_=Result.value,
                                    )
        
        return r[0] if r else 0

    def update_annotation(self, annotation: AnnotationsModel, user_tag: str) -> bool:    
    
        query = (
            "MATCH (a:Annotation {tag: $annotation_tag}) "
            "SET "
            " a.description = $description, "
            " a.publication = $publication, "
            " a.pubmed_id = $pubmed_id, "
            " a.source = $source, "
            " a.text = $text, "
            " a.group_tag = $group_tag, "
            " a.modified_at = timestamp(), "
            " a.s = toLower($text)+' '+toLower(coalesce($description,'')) "
            "WITH a "
            "OPTIONAL MATCH (a)-[r:ANNOTATES]->() DELETE r "
            "WITH a "
            "OPTIONAL MATCH (a)-[rb:BASED_ON]->() DELETE rb "
            "WITH a "
            "UNWIND $protein_tags AS protein_tag "
            "MATCH (p:Protein {tag: protein_tag}) "
            "MERGE (a)-[:ANNOTATES]->(p) "
            "WITH DISTINCT a "
            "MATCH (u:User {tag: $user_tag}) "
            "CREATE (u)-[:MODIFIED_ANNOTATION {modified_at: timestamp()}]->(a) "
            "RETURN TRUE "
        )

        r = self._driver.execute_query(query,
                                        annotation_tag=annotation.tag,
                                        text=annotation.text,
                                        description=annotation.description,
                                        publication=annotation.publication,
                                        pubmed_id=annotation.pubmed_id,
                                        source=annotation.source,
                                        protein_tags=annotation.protein_tags or [],
                                        group_tag=annotation.group_tag,
                                        user_tag=user_tag,
                                        routing_="w",
                                        result_transformer_=Result.value,
                                    )

        if annotation.submission_tags:
            submission_query = (
                "MATCH (a:Annotation {tag: $annotation_tag}) "
                "UNWIND $submission_tags AS sub_tag "
                "MATCH (s:Submission {tag: sub_tag}) "
                "MERGE (a)-[:BASED_ON]->(s) "
                "RETURN TRUE"
            )
            self._driver.execute_query(submission_query,
                                        annotation_tag=annotation.tag,
                                        submission_tags=annotation.submission_tags,
                                        routing_="w",
                                        result_transformer_=Result.value,
                                    )

        return r[0] if r else False
    

    def delete_annotation(self, tag: str, is_active: bool = False) -> bool:
        
        query = (
            "MATCH (a:Annotation {tag: $tag}) "
            "DETACH DELETE a "
        )

        r = self._driver.execute_query( query,
                                        tag=tag,
                                        is_active=is_active,
                                        routing_="w",
                                        result_transformer_=Result.value,
                                    )
        
        return True if r is not None else False
    


    def get_proteins_by_annotation_group(self, group_tag: str, submission_tag: str) -> Dict[str, List[str]]:

        query = (
            "MATCH (submission:Submission {tag: $submission_tag})-[:HAS_SAMPLE]->(:Sample)-[:QUANTIFIED]->(p:ProteinGroup)-[:HAS_PROTEINS]->(p:Protein) "
            "MATCH (ag:AnnotationGroup {tag: $group_tag})-[:HAS_ANNOTATION]->(a:Annotation)-[:ANNOTATES]->(p) "
            "RETURN a.tag AS annotation_tag, "
            "collect(DISTINCT p.tag) AS protein_tags "
        )

        r = self._driver.execute_query(
            query,
            group_tag=group_tag,
            submission_tag=submission_tag,
            routing_="r",
            result_transformer_=Result.data,
        )

        return {
            row["annotation_tag"]: row["protein_tags"]
            for row in r
        }

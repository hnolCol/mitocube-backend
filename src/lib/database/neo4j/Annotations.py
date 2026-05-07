import pandas as pd
from typing import Optional,List, Dict
import os

from services.random_generators import get_random_string
from services.encryption import create_hierarchical_hash
from neo4j import Driver, Result

from collections import defaultdict
from services.json import read_json

from config.models.annotations.annotations import ( AnnotationGroupsModel, AnnotationsModel )
from lib.database.abstract.Annotations import ( AnnotationGroupsABC, AnnotationsABC )

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

    
    def find( self, search_string: Optional[str] = None,  protein_tag: Optional[str] = None, search_in_annotations : bool = False, return_annotations : bool = False, limit : int = None) -> List[str]:

        query = "MATCH (ag:AnnotationGroup) "
        
        if protein_tag:
            query += "MATCH (ag)-[:HAS_ANNOTATION]->(a:Annotation)-[:ANNOTATES]->(:Protein {tag: $protein_tag}) "
        
        if search_string:
            
            if not search_in_annotations:
                query += "WHERE toLower(ag.text) CONTAINS toLower($search_string) "
            else:
            
                query += (
                    "MATCH (ag)-[:HAS_ANNOTATION]->(a:Annotation) "
                    "WHERE (toLower(a.description) CONTAINS toLower($search_string) "
                    "OR toLower(a.text) CONTAINS toLower($search_string)) OR (toLower(ag.text) CONTAINS toLower($search_string) OR toLower(ag.description) CONTAINS toLower($search_string)) "
                    "WITH collect(a.tag) as annotation_tags, ag "
                )

        if return_annotations:
            query += "RETURN {group_tag : ag.tag, annotation_tags : annotation_tags}"

        query += "RETURN ag.tag"
        
        if limit is not None:
            query += " LIMIT $limit"

        r = self._driver.execute_query( query,
                                        search_string=search_string,
                                        protein_tag=protein_tag,
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
    
    # def update(self, annotationgroup: AnnotationGroupsModel, user_tag: str) -> bool:
    #     """Updates an existing annotation group."""

    #     query = (
    #         "MATCH (ag:AnnotationGroup {tag: $tag}) "
    #         "SET "
    #         " ag.text = $text, "
    #         " ag.description = $description, "
    #         " ag.species = $species, "
    #         " ag.source = $source, "
    #         " ag.url = $url, "
    #         " ag.modified_at = timestamp() "
    #         "WITH ag "
    #         "MATCH (u:User {tag: $user_tag}) "
    #         "CREATE (u)-[:MODIFIED {modified_at: timestamp()}]->(ag) "
    #         "RETURN TRUE "
    #     )

    #     r = self._driver.execute_query( query,
    #                                     tag=annotationgroup.tag,
    #                                     text=annotationgroup.text,
    #                                     description=annotationgroup.description,
    #                                     species=annotationgroup.species,
    #                                     source=annotationgroup.source,
    #                                     url=annotationgroup.url,
    #                                     user_tag=user_tag,
    #                                     routing_="w",
    #                                     result_transformer_=Result.value,
    #                                 )
        
    #     return r[0] if r else False



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
        print(user_tag)
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
                                        protein_tags=annotation.protein_tags,
                                        group_tag=annotation.group_tag,
                                        routing_="w",
                                        result_transformer_=Result.value,
                                    )
        
        return r[0] if r else False


    def get(self, tag: str) -> AnnotationsModel:

        query = (
            "MATCH (ag:AnnotationGroup)-[:HAS_ANNOTATION]->(a:Annotation {tag: $tag}) "
            "OPTIONAL MATCH (a)-[:ANNOTATES]->(p:Protein) "
            "RETURN "
            " properties(a) AS a_props, "
            " ag.tag AS group_tag, "
            " collect(p.tag) AS protein_tags "
        )
        
        r = self._driver.execute_query( query,
                                        tag=tag,
                                        routing_="r",
                                        result_transformer_=Result.data,
                                    )
                                    
        if not r:
            raise Exception("Annotation not found")
        
        data = r[0]["a_props"]
        data["group_tag"] = r[0]["group_tag"]
        data["protein_tags"] = r[0]["protein_tags"]
        
        return AnnotationsModel(**data)

    def find(self, search_string: Optional[str] = None, group_tags: Optional[List[str]] = None,  protein_tags: Optional[List[str]] = None, limit: Optional[int] = None, group_by_group = False) -> List[str]:

        
        query = (
                "MATCH (ag:AnnotationGroup)-[:HAS_ANNOTATION]->(a:Annotation) "
            )
        if group_tags is not None:
            query += "WHERE ag.tag IN $group_tags "
                
        if protein_tags is not None:
            
            if group_tags is not None:
                query += "AND "
            else:
                query += "WHERE "
            
            query = (
                "EXISTS {(a)-[:ANNOTATES]->(p:Protein) WHERE p.tag in $protein_tags} "
            )

        if search_string is not None and search_string != "":
            if protein_tags is not None or group_tags is not None:
                query += "AND "
            else:
                query += "WHERE "
            query += "a.s CONTAINS $search_string "
            
        if group_by_group:
            query += "RETURN ag.tag, a.tag "
        else: 
            query += "RETURN a.tag "
        
        if limit is not None:
            query += "LIMIT $limit"
        
        r = self._driver.execute_query( query,
                                        group_tags=group_tags,
                                        protein_tags=protein_tags,
                                        limit=limit,
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

    def get_protein_tags(self, tag: str) -> List[str]:

        query = (
            "MATCH (:Annotation {tag: $tag})-[:ANNOTATES]->(p:Protein) "
            "RETURN p.tag"
        )

        r = self._driver.execute_query( query,
                                        tag=tag,
                                        routing_="r",
                                        result_transformer_=Result.value,
                                    )
        
        return r
    
    def get_text(self, group_tag: str, text: str) -> bool:
        query = (
            "MATCH (a:Annotation {group_tag: $group_tag}) "
            "WHERE toLower(a.text) = toLower($text) "
            "RETURN count(a) > 0 AS exists"
        )

        result = self._driver.execute_query(
                query,
                group_tag=group_tag,
                text=text,
                result_transformer_=lambda r: r.single()["exists"],
            )

        return bool(result)

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
            "UNWIND $protein_tags AS protein_tag "
            "MATCH (p:Protein {tag: protein_tag}) "
            "MERGE (a)-[:ANNOTATES]->(p) "
            "WITH a "
            "MATCH (u:User {tag: $user_tag}) "
            "CREATE (u)-[:MODIFIED_ANNOTATION {modified_at: timestamp()}]->(a) "
            "RETURN TRUE "
        )
        r = self._driver.execute_query( query,
                                        annotation_tag=annotation.tag,
                                        text=annotation.text,
                                        description=annotation.description,
                                        publication=annotation.publication,
                                        pubmed_id=annotation.pubmed_id,
                                        source=annotation.source,
                                        protein_tags=annotation.protein_tags,
                                        group_tag=annotation.group_tag,
                                        user_tag=user_tag,
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
            "MATCH (submission:Submission {tag: $submission_tag})-[:HAS_SAMPLE]->(:Sample)-[:QUANTIFIED]->(p:Protein) "
            "MATCH (ag:AnnotationGroup {tag: $group_tag})-[:HAS_ANNOTATION]->(a:Annotation)-[:ANNOTATES]->(p) "
            "RETURN a.tag AS annotation_tag, "
            "collect(DISTINCT p.tag) AS protein_tags"
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

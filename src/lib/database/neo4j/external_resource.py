import os
import pandas as pd
from typing import List, Optional
from neo4j import Driver, Result

from services.json import read_json
from lib.database.abstract.external_resource import ExternalResourceABC
from lib.database.abstract.Crosslink import CrosslinkABC
from lib.database.abstract.ConditionApplications import ConditionApplicationABC
from config.models.external_resource import ExternalResourceInsertModel, ExternalResourceModel
from config.models.crosslink import CrosslinkInsertModel
from config.models.conditions_applications import ConditionApplicationTreeModel
from config.models.attributes import AttributeTree


class Neo4jExternalResources(ExternalResourceABC):
    """
    Neo4j layout:
        (ExternalResource {external, link, title})-[:HAS_XL]->(XL)
        (ExternalResource)-[:HAS_APPLICATION]->(ConditionApplication)
        (XL)-[:LINKS {position, peptide_sequence}]->(Protein)
        (XL)-[:LINKS {position, peptide_sequence}]->(Protein)
    """

    def __init__(self, driver: Driver, crosslinks: CrosslinkABC, condition_applications: ConditionApplicationABC) -> None:
        self._driver = driver
        self._crosslinks = crosslinks
        self._condition_applications = condition_applications

    def exists(self, tag: str) -> bool:
        query = "WITH EXISTS { (r:ExternalResource {tag: $tag}) } AS exists RETURN exists"
        r = self._driver.execute_query(query, tag=tag, routing_="r", result_transformer_=Result.value)
        return r[0]

    def _insert_condition_applications(self, resource_tag: str, condition_applications: List[AttributeTree]) -> None:
        """Insert condition applications for an external resource, mirroring
        Neo4jPhenotypeAssociations._insert_condition_applications: each top-level
        attribute's children are split into individual trees so condition-application
        nodes are shared/deduped by content across parents, then merged onto the
        resource in one batch."""
        ts = []
        for attribute_tree in condition_applications:
            for c in attribute_tree.children:
                updated_tree = AttributeTree(
                    tag=attribute_tree.tag,
                    type=attribute_tree.type,
                    value=attribute_tree.value,
                    children=[c]
                )
                tag = self._condition_applications.insert(condition_application=updated_tree)
                ts.append(tag)

        if not ts:
            return

        query = (
            "MATCH (r:ExternalResource {tag: $resource_tag}) "
            "MATCH (ca:ConditionApplication) "
            "WHERE ca.tag IN $tags "
            "MERGE (r)-[rel:HAS_APPLICATION]->(ca) "
            "SET rel.created_at = timestamp() "
        )
        self._driver.execute_query(query, routing_="w", resource_tag=resource_tag, tags=ts)

    def insert(self, data: ExternalResourceInsertModel) -> bool:
        query = (
            "MERGE (r:ExternalResource {tag: $tag}) "
            "ON CREATE SET "
            "  r.created_at = timestamp(), "
            "  r.title = $title, "
            "  r.link = $link, "
            "  r.doi = $doi, "
            "  r.type = $type, "
            "  r.author = $author, "
            "  r.publication_date = $publication_date, "
            "  r.external = $external "
            "ON MATCH SET "
            "  r.title = $title, "
            "  r.link = $link, "
            "  r.doi = $doi, "
            "  r.type = $type, "
            "  r.author = $author, "
            "  r.publication_date = $publication_date, "
            "  r.external = $external "
            "RETURN true AS ok"
        )
        r = self._driver.execute_query(
            query,
            tag=data.tag,
            title=data.title,
            link=data.link,
            doi=data.doi,
            type=data.type,
            author=data.author,
            publication_date=data.publication_date,
            external=data.is_external,
            routing_="w",
            result_transformer_=Result.value,
        )
        ok = bool(r) and r[0]

        if ok and data.condition_applications:
            self._insert_condition_applications(data.tag, data.condition_applications)

        return ok

    def get(self, tag: str) -> ExternalResourceModel:
        query = (
            "MATCH (r:ExternalResource {tag: $tag}) "
            "RETURN properties(r)"
        )
        r = self._driver.execute_query(
            query, tag=tag, routing_="r", result_transformer_=Result.value
        )
        if not r:
            raise Exception("External resource not found")
        return ExternalResourceModel(**r[0])

    def find(self, limit: Optional[int] = None) -> List[str]:
        query = "MATCH (r:ExternalResource) RETURN r.tag "
        if limit is not None:
            query += "LIMIT $limit"

        r = self._driver.execute_query(
            query, limit=limit, routing_="r", result_transformer_=Result.value
        )
        return r

    def get_condition_applications(self, tag: str) -> List[str]:
        query = (
            "MATCH (r:ExternalResource {tag: $tag})-[:HAS_APPLICATION]->(ca:ConditionApplication) "
            "OPTIONAL MATCH (ca)-[:OF_ATTRIBUTE]->(attr:Attribute) "
            "OPTIONAL MATCH (ca)-[:INSTANCE_OF]->(val) "
            "RETURN "
            "  coalesce(attr.text, attr.name, attr.tag) AS attribute_label, "
            "  coalesce(val.text, val.name, val.tag, ca.tag) AS value_label"
        )
        r = self._driver.execute_query(query, tag=tag, routing_="r", result_transformer_=Result.data)

        labels = []
        for row in r:
            a, v = row.get("attribute_label"), row.get("value_label")
            if a and v:
                labels.append(f"{a}: {v}")
            elif v:
                labels.append(str(v))
            elif a:
                labels.append(str(a))
        return labels
    
    def link_crosslink(self, resource_tag: str, crosslink_tag: str) -> bool:
        query = (
            "MATCH (r:ExternalResource {tag: $resource_tag}) "
            "MATCH (xl:XL {tag: $crosslink_tag}) "
            "MERGE (r)-[:HAS_XL]->(xl) "
            "RETURN true AS ok"
        )
        r = self._driver.execute_query(
            query,
            resource_tag=resource_tag,
            crosslink_tag=crosslink_tag,
            routing_="w",
            result_transformer_=Result.value,
        )
        return bool(r) and r[0]

    def find_crosslinks(self, resource_tag: str, limit: int = 100) -> List[dict]:
        query = (
            "MATCH (r:ExternalResource {tag: $resource_tag})-[:HAS_XL]->(xl:XL) "
            "MATCH (xl)-[la:LINKS]->(pa:Protein) "
            "MATCH (xl)-[lb:LINKS]->(pb:Protein) "
            "WHERE pa.tag <> pb.tag "
            "RETURN xl.tag AS tag, xl.score AS score, "
            "  pa.tag AS protein_tag_a, pb.tag AS protein_tag_b, "
            "  la.position AS pos_a, lb.position AS pos_b, "
            "  la.peptide_sequence AS peptide_a, lb.peptide_sequence AS peptide_b "
            "LIMIT $limit"
        )
        r = self._driver.execute_query(
            query,
            resource_tag=resource_tag,
            limit=limit,
            routing_="r",
            result_transformer_=Result.data,
        )
        return r

    def find_by_protein(self, protein_tag: str) -> List[dict]:
        query = (
            "MATCH (p:Protein {tag: $protein_tag})<-[:LINKS]-(xl:XL) "
            "MATCH (r:ExternalResource)-[:HAS_XL]->(xl) "
            "RETURN r.tag AS tag, r.title AS title, r.link AS link, r.author AS author, "
            "  r.publication_date AS publication_date, r.doi AS doi, r.type AS type, "
            "  count(xl) AS crosslink_count"
        )
        r = self._driver.execute_query(
            query, protein_tag=protein_tag, routing_="r", result_transformer_=Result.data,
        )
        return r

    def _utils_insert_from_file(self, file_path: str, folder_path: str = "") -> None:
        """Inserts external resources and their XL data from a config JSON file.

        JSON format:
        {
          "resources": [
            {
              "external_resource": {
                "title": "...",
                "link": "...",
                "doi": "...",
                "type": "publication"
              },
              "crosslinks": [
                {
                  "file_path": "crosslinks.txt",
                  "protein_tag_a_column": "protein_tag_a",
                  "protein_tag_b_column": "protein_tag_b",
                  "pos_a_column": "pos_a",
                  "pos_b_column": "pos_b",
                  "peptide_a_column": "peptide_a",
                  "peptide_b_column": "peptide_b",
                  "score_column": "score",
                  "sep": "\\t"
                }
              ]
            }
          ]
        }
        """
        config = read_json(file_path)

        if "resources" not in config:
            raise ValueError("JSON file must have a 'resources' key.")

        for resource_config in config["resources"]:
            er_config = resource_config["external_resource"]
            resource = ExternalResourceInsertModel(**er_config)

            self.insert(resource)
            print(f"  ExternalResource '{resource.title}' ({resource.tag}) ready.")

            for entry in resource_config.get("crosslinks", []):
                self._insert_crosslinks_from_entry(entry, resource.tag, folder_path)

            print("  Done.")

    def _insert_crosslinks_from_entry(self, entry: dict, resource_tag: str, folder_path: str) -> None:
        data_path = os.path.join(folder_path, entry["file_path"])
        sep = entry.get("sep", "\t")
        encoding = entry.get("encoding", "utf-8")

        df = pd.read_csv(data_path, sep=sep, encoding=encoding)

        protein_tag_a_col = entry.get("protein_tag_a_column", "protein_tag_a")
        protein_tag_b_col = entry.get("protein_tag_b_column", "protein_tag_b")
        pos_a_col = entry.get("pos_a_column", "pos_a")
        pos_b_col = entry.get("pos_b_column", "pos_b")
        peptide_a_col = entry.get("peptide_a_column", None)
        peptide_b_col = entry.get("peptide_b_column", None)
        score_col = entry.get("score_column", "score")

        inserted, skipped = 0, 0

        for _, row in df.iterrows():
            try:
                data = CrosslinkInsertModel(
                    protein_tag_a=str(row[protein_tag_a_col]),
                    protein_tag_b=str(row[protein_tag_b_col]),
                    pos_a=int(row[pos_a_col]),
                    pos_b=int(row[pos_b_col]),
                    peptide_a=str(row[peptide_a_col]) if peptide_a_col and not pd.isna(row.get(peptide_a_col)) else None,
                    peptide_b=str(row[peptide_b_col]) if peptide_b_col and not pd.isna(row.get(peptide_b_col)) else None,
                    score=float(row[score_col]) if score_col and not pd.isna(row.get(score_col)) else None,
                )
            except (ValueError, KeyError):
                skipped += 1
                continue

            if self._crosslinks.insert_external(data, resource_tag=resource_tag):
                inserted += 1
            else:
                skipped += 1

        print(f"    Inserted {inserted}, skipped {skipped} crosslinks from {entry['file_path']}")
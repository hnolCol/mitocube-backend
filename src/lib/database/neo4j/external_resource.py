import os
import pandas as pd
from typing import List, Optional
from neo4j import Driver, Result

from services.json import read_json
from lib.database.abstract.external_resource import ExternalResourceABC
from lib.database.abstract.Crosslink import CrosslinkABC
from config.models.external_resource import ExternalResourceInsertModel, ExternalResourceModel
from config.models.crosslink import CrosslinkInsertModel


class Neo4jExternalResources(ExternalResourceABC):
    """
    Neo4j layout:
        (ExternalResource {external, link, title})-[:HAS_XL]->(XL)
        (XL)-[:LINKS {position, peptide_sequence}]->(Protein)
        (XL)-[:LINKS {position, peptide_sequence}]->(Protein)
    """

    def __init__(self, driver: Driver, crosslinks: CrosslinkABC) -> None:
        self._driver = driver
        self._crosslinks = crosslinks

    def exists(self, tag: str) -> bool:
        query = "WITH EXISTS { (r:ExternalResource {tag: $tag}) } AS exists RETURN exists"
        r = self._driver.execute_query(query, tag=tag, routing_="r", result_transformer_=Result.value)
        return r[0]

    def insert(self, data: ExternalResourceInsertModel) -> bool:
        query = (
            "MERGE (r:ExternalResource {tag: $tag}) "
            "ON CREATE SET "
            "  r.created_at = timestamp(), "
            "  r.title = $title, "
            "  r.link = $link, "
            "  r.doi = $doi, "
            "  r.type = $type, "
            "  r.external = true "
            "ON MATCH SET "
            "  r.title = $title, "
            "  r.link = $link, "
            "  r.doi = $doi, "
            "  r.type = $type, "
            "  r.external = true "
            "RETURN true AS ok"
        )
        r = self._driver.execute_query(
            query,
            tag=data.tag,
            title=data.title,
            link=data.link,
            doi=data.doi,
            type=data.type,
            routing_="w",
            result_transformer_=Result.value,
        )
        return bool(r) and r[0]

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
            "  r.cell_type AS cell_type, r.cross_linkers AS cross_linkers, "
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
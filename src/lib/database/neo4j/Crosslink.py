from neo4j import Driver, Result
from typing import List, Optional
from lib.database.abstract.Crosslink import CrosslinkABC
from config.models.crosslink import CrosslinkInsertModel
from typing import Dict, Any, List


class Neo4jCrosslinks(CrosslinkABC):
    """
    Neo4j layout:
        (ExternalResource {external, link, title})-[:HAS_XL]->(XL)
        (XL)-[:LINKS {position, peptide_sequence}]->(Protein)
        (XL)-[:LINKS {position, peptide_sequence}]->(Protein)
    """

    def __init__(self, driver: Driver):
        self._driver = driver

    def exists(self, tag: str) -> bool:
        query = "WITH EXISTS { (xl:XL {tag: $tag}) } AS exists RETURN exists"
        r = self._driver.execute_query(query, tag=tag, routing_="r", result_transformer_=Result.value)
        return r[0]

    def insert(self, data: CrosslinkInsertModel, user_tag: str) -> bool:
        "Inserts a new XL into the database. Returns True if successful, False otherwise."
        query = (
            "MERGE (xl:XL {tag: $tag}) "
            "ON CREATE SET xl.created_at = timestamp(), xl.score = $score, xl.is_active = true "
            "ON MATCH  SET xl.modified_at = timestamp(), xl.score = $score "
            "WITH xl "
            "MATCH (u:User {tag: $user_tag}) "
            "MERGE (u)-[:CREATED {created_at: timestamp()}]->(xl) "
            "WITH xl "
            "MATCH (pa:Protein {tag: $protein_tag_a}) "
            "MATCH (pb:Protein {tag: $protein_tag_b}) "
            "MERGE (xl)-[:LINKS {position: $pos_a, peptide_sequence: $peptide_a}]->(pa) "
            "MERGE (xl)-[:LINKS {position: $pos_b, peptide_sequence: $peptide_b}]->(pb) "
            "RETURN true AS ok"
            # "MERGE (pa:Protein)<-[:LINKS {position: $pos_a, peptide_sequence: $peptide_a}]-(xl)-[:LINKS {position: $pos_b, peptide_sequence: $peptide_b}]->(pb:Protein ) "
        )
        r = self._driver.execute_query(query, tag=data.tag, score=data.score,
            user_tag=user_tag,
            protein_tag_a=data.protein_tag_a, protein_tag_b=data.protein_tag_b,
            pos_a=data.pos_a, pos_b=data.pos_b,
            peptide_a=data.peptide_a or "", peptide_b=data.peptide_b or "",
            routing_="w", result_transformer_=Result.value)
        return bool(r) and r[0]

    def insert_external(self, data: CrosslinkInsertModel, resource_tag: str) -> bool:
        "Inserts an XL sourced from an external resource (no User/CREATED edge)."
        query = (
            "MATCH (r:ExternalResource {tag: $resource_tag}) "
            "MATCH (pa:Protein {tag: $protein_tag_a}) "
            "MATCH (pb:Protein {tag: $protein_tag_b}) "
            "MERGE (xl:XL {tag: $tag}) "
            "ON CREATE SET xl.created_at = timestamp(), xl.score = $score, xl.is_active = true "
            "ON MATCH  SET xl.score = $score "
            "MERGE (r)-[:HAS_XL]->(xl) "
            "MERGE (xl)-[:LINKS {position: $pos_a, peptide_sequence: $peptide_a}]->(pa) "
            "MERGE (xl)-[:LINKS {position: $pos_b, peptide_sequence: $peptide_b}]->(pb) "
            "RETURN true AS ok"
        )
        r = self._driver.execute_query(query, tag=data.tag, score=data.score,
            resource_tag=resource_tag,
            protein_tag_a=data.protein_tag_a, protein_tag_b=data.protein_tag_b,
            pos_a=data.pos_a, pos_b=data.pos_b,
            peptide_a=data.peptide_a or "", peptide_b=data.peptide_b or "",
            routing_="w", result_transformer_=Result.value)
        return bool(r) and r[0]

    def get(self, tag: str) -> dict:
        query = (
            "MATCH (xl:XL {tag: $tag}) "
            "MATCH (xl)-[la:LINKS]->(pa:Protein) "
            "MATCH (xl)-[lb:LINKS]->(pb:Protein) "
            "WHERE pa.tag <> pb.tag "
            "OPTIONAL MATCH (r:ExternalResource)-[:HAS_XL]->(xl) "
            "RETURN xl.tag AS tag, xl.score AS score, "
            "xl.created_at AS created_at, "
            "pa.tag AS protein_tag_a, pb.tag AS protein_tag_b, "
            "la.position AS pos_a, lb.position AS pos_b, "
            "la.peptide_sequence AS peptide_a, lb.peptide_sequence AS peptide_b, "
            "r.tag AS resource_tag, r.title AS resource_title"
        )
        r = self._driver.execute_query(query, tag=tag, routing_="r", result_transformer_=Result.data)
        return r[0] if r else {}

    def find(self, protein_tag: str, resource_tag: Optional[str] = None, limit: Optional[int] = None) -> List[dict]:
        query = (
            "MATCH (p:Protein {tag: $protein_tag})<-[pl:LINKS]-(xl:XL)-[ol:LINKS]->(other:Protein) "
            "WHERE pl.peptide_sequence <> ol.peptide_sequence "
            "AND (p.tag <> other.tag OR pl.peptide_sequence <> ol.peptide_sequence) "
        )

        if resource_tag is not None:
            query += "MATCH (r:ExternalResource {tag: $resource_tag})-[:HAS_XL]->(xl) "
        else:
            query += "OPTIONAL MATCH (r:ExternalResource)-[:HAS_XL]->(xl) "

        query += (
            "WITH xl, p, other, pl, ol, collect(r.tag)[0] AS resource_tag, collect(r.title)[0] AS resource_title "
            "RETURN xl.tag AS tag, xl.score AS score, "
            "p.tag AS protein_tag_a, other.tag AS protein_tag_b, "
            "pl.position AS pos_a, ol.position AS pos_b, "
            "pl.peptide_sequence AS peptide_a, ol.peptide_sequence AS peptide_b, "
            "resource_tag, resource_title "
        )

        if limit is not None:
            query += "LIMIT $limit"

        r = self._driver.execute_query(query, protein_tag=protein_tag, resource_tag=resource_tag,
            limit=limit, routing_="r", result_transformer_=Result.data)
        return r
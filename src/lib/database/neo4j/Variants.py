from neo4j import Driver, Result
from typing import List
from lib.database.abstract.Variants import VariantABC
from config.models.variants import VariantModel, VariantInputModel

class Neo4jVariants(VariantABC):

    def __init__(self, driver: Driver) -> None:
        self._driver = driver

    def count(self) -> int:
        query = ("MATCH (v:Variant) "
                "RETURN count(v) "
        )
        r = self._driver.execute_query(query, routing_="r", result_transformer_=Result.value)
        return r[0] if r else 0

    def exists(self, tag: str) -> bool:
        query = (
            "WITH EXISTS {(v:Variant {tag: $tag})} AS variant_exists "
            "RETURN variant_exists "
        )
        r = self._driver.execute_query(query, tag=tag, routing_="r", result_transformer_=Result.value)
        return r[0] if r else False 

    def insert(self, variant: VariantInputModel, user_tag: str) -> bool:
        query = (
            "MERGE (v:Variant {tag: $tag}) "
            "ON CREATE SET v.created_at = timestamp(), v.title = $title, "
            "              v.clinical_significance = $clinical_significance, "
            "              v.consequence = $consequence, v.rsid = $rsid, "
            "              v.gene_symbol = $gene_symbol, v.is_active = true "
            "ON MATCH  SET v.modified_at = timestamp(), v.title = $title, "
            "              v.clinical_significance = $clinical_significance "
            "WITH v "
            "MATCH (d:Disease {tag: $disease_tag}) "
            "MERGE (v)-[:LINKED_TO]->(d) "
            "RETURN true AS ok"
        )
        r = self._driver.execute_query(query,
            tag=variant.tag, title=variant.title,
            clinical_significance=variant.clinical_significance,
            consequence=variant.consequence, rsid=variant.rsid,
            gene_symbol=variant.gene_symbol,
            disease_tag=variant.disease_tag,
            routing_="w", database_="neo4j", result_transformer_=Result.value)

        # link protein by gene symbol match against p.s
        if variant.gene_symbol:
            self._driver.execute_query(
                "MATCH (v:Variant {tag: $tag}) "
                "MATCH (p:Protein) WHERE p.s CONTAINS toLower($gene_symbol) "
                "MERGE (v)-[:EFFECTS]->(p) ",
                tag=variant.tag, gene_symbol=variant.gene_symbol,
                routing_="w", database_="neo4j"
            )

        return bool(r)

    def get(self, tag: str) -> VariantModel | None:
        query = (
            "MATCH (v:Variant {tag: $tag}) "
            "OPTIONAL MATCH (v)-[:LINKED_TO]->(d:Disease) "
            "OPTIONAL MATCH (v)-[:EFFECTS]->(p:Protein) "
            "RETURN v.tag AS tag, v.title AS title, v.clinical_significance AS clinical_significance, "
            "       v.consequence AS consequence, v.rsid AS rsid, v.gene_symbol AS gene_symbol, "
            "       d.tag AS disease_tag, p.tag AS protein_tag, v.created_at AS created_at"
        )
        r = self._driver.execute_query(query, tag=tag, routing_="r", result_transformer_=Result.data)
        return VariantModel(**r[0]) if r else None

    def find_by_protein(self, protein_tag: str, limit: int = 20) -> List[VariantModel]:
        query = (
            "MATCH (v:Variant)-[:EFFECTS]->(p:Protein {tag: $protein_tag}) "
            "RETURN properties(v) LIMIT $limit"
        )
        r = self._driver.execute_query(query, protein_tag=protein_tag, limit=limit, routing_="r", result_transformer_=Result.value)
        return [VariantModel(**ri) for ri in r]

    def find_by_disease(self, disease_tag: str, limit: int = 20) -> List[VariantModel]:
        query = (
            "MATCH (v:Variant)-[:LINKED_TO]->(d:Disease {tag: $disease_tag}) "
            "RETURN properties(v) LIMIT $limit"
        )
        r = self._driver.execute_query(query, disease_tag=disease_tag, limit=limit, routing_="r", result_transformer_=Result.value)
        return [VariantModel(**ri) for ri in r]

    def delete(self, tag: str, is_active: bool = False) -> bool:
        query = ( 
            "MATCH (v:Variant {tag: $tag}) "
            "SET v.is_active = $is_active "
            "RETURN true AS ok"
        )
        r = self._driver.execute_query(
            query, 
            tag=tag, is_active=is_active, routing_="w", result_transformer_=Result.value)
        return bool(r)
from neo4j import Driver, Result
from typing import List
from lib.database.abstract.Diseases import DiseaseABC
from config.models.diseases import DiseaseModel, DiseaseInputModel

class Neo4jDiseases(DiseaseABC):

    def __init__(self, driver: Driver) -> None:
        self._driver = driver

    def count(self) -> int:
        "Returns the total number of diseases in the database."
        query = ("MATCH (d:Disease) "
                "RETURN count(d) "
        )
        r = self._driver.execute_query(query, routing_="r", result_transformer_=Result.value)
        return r[0] if r else 0


    def exists(self, tag: str) -> bool:
        "Checks if a disease with the given tag exists in the database."
        query = (
            "WITH EXISTS {(d:Disease {tag: $tag})} AS disease_exists "
            "RETURN disease_exists "
        )
        r = self._driver.execute_query(query, tag=tag, routing_="r", result_transformer_=Result.value)
        return r[0] if r else False


    def insert(self, disease: DiseaseInputModel, user_tag: str) -> bool:
        "Inserts a new disease into the database. Returns True if successful, False otherwise."
        query = (
            "MERGE (d:Disease {tag: $tag}) "
            "ON CREATE SET d.created_at = timestamp(), d.text = $text, d.description = $description, d.is_active = true, d.s = toLower($text) "
            "ON MATCH  SET d.modified_at = timestamp(), d.text = $text, d.description = $description "
            "WITH d "
            "MATCH (u:User {tag: $user_tag}) "
            "MERGE (u)-[:CREATED {created_at: timestamp()}]->(d) "
            "RETURN true AS ok"
        )
        r = self._driver.execute_query(query, tag=disease.tag, text=disease.text,
            description=disease.description, user_tag=user_tag,
            routing_="w", result_transformer_=Result.value)
        return bool(r)

    def get(self, tags: List[str] = None, limit: int = 20) -> List[DiseaseModel]:
        "Retrieves diseases from the database. If tags are provided, retrieves diseases matching those tags. Otherwise, retrieves all diseases up to the specified limit."
        query = "MATCH (d:Disease) "
        if tags:
            query += "WHERE d.tag IN $tags "
        query += "RETURN properties(d) LIMIT $limit"
        r = self._driver.execute_query(query, tags=tags, limit=limit, routing_="r", result_transformer_=Result.value)
        return [DiseaseModel(**ri) for ri in r]

    def find(self, query: str = "", limit: int = 20) -> List[DiseaseModel]:
        "Searches for diseases in the database that match the given query string. Returns a list of matching diseases up to the specified limit."
        query = (
            "MATCH (d:Disease) "
            "WHERE d.s CONTAINS $query, "
            "RETURN properties(d) LIMIT $limit"
        )
        r = self._driver.execute_query(query, limit=limit, routing_="r", result_transformer_=Result.value)
        return [DiseaseModel(**ri) for ri in r]

    def delete(self, tag: str, is_active: bool = False) -> bool:
        "Deletes a disease from the database. If is_active is True, performs a soft delete (e.g., marks the disease as inactive). If False, performs a hard delete. Returns True if successful, False otherwise."
        query = (
            "MATCH (d:Disease {tag: $tag}) "
            "SET d.is_active = $is_active "
            "RETURN true AS ok"
        )
        r = self._driver.execute_query(
            query,
            tag=tag, is_active=is_active, routing_="w", result_transformer_=Result.value)
        return bool(r)
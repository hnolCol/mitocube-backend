import pandas as pd
from typing import Optional,List

from neo4j import Driver, Result

from config.models.annotations.annotations import ( AnnotationGroupModel, AnnotationModel )
from lib.database.abstract.Annotations import ( AnnotationGroupABC, AnnotationABC )

class Neo4JAnnotationGroup(AnnotationGroupABC):

    def __init__(self, driver : Driver) -> None:
        self._driver = driver

    def exists(self, tag: str) -> bool:
        """Checks if an annoation groupt exists."""

        query = (
            "WITH EXISTS {(ag:AnnotationGroup {tag: $annotation_group_tag})} AS ag_exists "
            "RETURN ag_exists "
        )

        r = self._driver.execute_query(query, annotation_group_tag=tag, result_transformer_=Result.value)
        return r[0]
    
    def insert(self, annotationgroup: AnnotationGroupModel) -> bool:
        """Creates a new annnotation group."""

        query = (
           "MERGE (ag:AnnotationGroup {tag: $tag}) "
            "ON CREATE "
            "SET ag.name = $name, "
            "    ag.description = $description, "
            "    ag.created_at = timestamp() "
            "RETURN TRUE"
        )

        r = self._driver.execute_query( query,
                                        tag=annotationgroup.tag,
                                        name=annotationgroup.name,
                                        description=annotationgroup.description,
                                        routing_="w",
                                        result_transformer_=Result.value,
                                    )
        
        return r[0] if r else False
    
    def get(self, tag: str) -> AnnotationGroupModel:
       
        query = (
            "MATCH (ag:AnnotationGroup {tag: $tag}) "
            "RETURN properties(ag)"
        )

        r = self._driver.execute_query( query,
                                        tag=tag,
                                        routing_="r",
                                        result_transformer_=Result.value,
                                    )

        return AnnotationGroupModel(**r[0])

    def find(self) -> List[AnnotationGroupModel]:
        
        query = (
            "MATCH (ag:AnnotationGroup) "
            "RETURN properties(ag)"
        )

        r = self._driver.execute_query( query,
                                        routing_="r",
                                        result_transformer_=Result.value,
                                    )

        return [AnnotationGroupModel(**g) for g in r]

    def get_annotations(self, group_tag: str) -> List[str]:
        query = (
            "MATCH (:AnnotationGroup {tag: $tag})-[:HAS_ANNOTATION]->(a:Annotation) "
            "RETURN a.tag"
        )

        r = self._driver.execute_query( query,
                                        tag=group_tag,
                                        routing_="r",
                                        result_transformer_=Result.value,
                                    )
        return r


class Neo4JAnnotation(AnnotationABC):

    def __init__(self, driver: Driver) -> None:
        self._driver = driver

    def exists(self, tag: str) -> bool:
        query = (
            "WITH EXISTS {(a:Annotation {tag: $annotation_tag})} AS a_exists "
            "RETURN a_exists "
        )

        r = self._driver.execute_query( query,
                                        tag=tag,
                                        routing_="r",
                                        result_transformer_=Result.value,
                                    )
        return r[0] if r else False

    def add(self, annotation: AnnotationModel) -> bool:
        query = (
            "MATCH (ag:AnnotationGroup {tag: $group_tag}) "
            "MERGE (a:Annotation {tag: $tag}) "
            "ON CREATE "
            "SET a.description = $description, "
            "    a.publication = $publication, "
            "    a.pubmed_id = $pubmed_id, "
            "    a.created_at = timestamp() "
            "MERGE (ag)-[:HAS_ANNOTATION]->(a) "
            "RETURN TRUE"
        )

        r = self._driver.execute_query( query,
                                        tag=annotation.tag,
                                        description=annotation.description,
                                        publication=annotation.publication,
                                        pubmed_id=annotation.pubmed_id,
                                        group_tag=annotation.group_tag,
                                        routing_="w",
                                        result_transformer_=Result.value,
                                    )

        return r[0] if r else False

    def get(self, tag: str) -> AnnotationModel:
        
        query = (
            "MATCH (a:Annotation {tag: $tag}) "
            "MATCH (ag:AnnotationGroup)-[:HAS_ANNOTATION]->(a) "
            "RETURN properties(a) AS annotation_props "
        )

        r = self._driver.execute_query( query,
                                        tag=tag,
                                        routing_="r",
                                        result_transformer_=Result.value,
                                    )

        if not r:
            raise Exception(f"Annotation {tag} not found")

        return AnnotationModel(**r[0])


    def find( self, tag: str = None, annotation_group_tag: Optional[str] = None, protein_tag: Optional[str] = None,) -> List[str]:

        """
            """
        
        if tag is not None:
            query = (
                "MATCH (a:Annotation) "
                "WHERE a.tag = $tag "
            )

        elif annotation_group_tag is not None:
            query = (
                "MATCH (:AnnotationGroup {tag: $annotation_group_tag})-[:HAS_ANNOTATION]->(a:Annotation) "
            )

        elif protein_tag is not None:
            query = (
                "MATCH (a:Annotation)-[:ANNOTATES]->(p:Protein) "
                "WHERE p.tag = $protein_tag "
            )

        else:
            query = (
                "MATCH (a:Annotation) "
            )

        query += "RETURN a.tag"

        r = self._driver.execute_query( query,
                                        tag=tag,
                                        annotation_group_tag=annotation_group_tag,
                                        protein_tag=protein_tag,
                                        routing_="r",
                                        result_transformer_=Result.value,
                                    )

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

    def get_protein_ids(self, tag: str) -> List[str]:
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

    def isin(self, tag: str, protein_ids: List[str]) -> pd.Series:
        query = (
            "MATCH (p:Protein) "
            "WHERE p.tag IN $protein_ids "
            "RETURN p.tag AS tag, "
            "EXISTS {(:Annotation {tag: $annotation_tag})-[:ANNOTATES]->(p)} AS isin"
        )

        r = self._driver.execute_query( query,
                                        protein_ids=protein_ids,
                                        annotation_tag=tag,
                                        routing_="r",
                                        result_transformer_=Result.to_df,
        )

        if r.empty:
            return pd.Series([], dtype=bool)

        r = r.set_index("tag")
        return r["isin"]


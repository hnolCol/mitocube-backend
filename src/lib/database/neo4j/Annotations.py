import pandas as pd
from typing import Optional,List

from neo4j import Driver, Result

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
    
    def insert(self, annotationgroup: AnnotationGroupsModel) -> bool:
        """Creates a new annnotation group."""

        query = (
           "MERGE (ag:AnnotationGroup {tag: $tag}) "
            "ON CREATE "
            "SET ag.text = $text, "
            "    ag.description = $description, "
            "    ag.created_at = timestamp() "
            "RETURN TRUE"
        )

        r = self._driver.execute_query( query,
                                        tag=annotationgroup.tag,
                                        text=annotationgroup.text,
                                        description=annotationgroup.description,
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

    def find(self, search_string: Optional[str] = None, protein_tag: Optional[str] = None) -> List[str]:
        
        # query = (
        #     "MATCH (ag:AnnotationGroup) "
        #     "RETURN properties(ag)"
        # )

        # r = self._driver.execute_query( query,
        #                                 routing_="r",
        #                                 result_transformer_=Result.value,
        #                             )

        # return [AnnotationGroupsModel(**g) for g in r]
        
        query = "MATCH (ag:AnnotationGroup) "

        
        if protein_tag:
            query += "MATCH (a)-[:ANNOTATES]->(:Protein {tag: $protein_tag}) "

        if search_string:
            query += (
                "WHERE toLower(a.description) CONTAINS toLower($search_string) "
            )

        query += "RETURN ag.tag"

        r = self._driver.execute_query( query,
                                        search_string=search_string,
                                        protein_tag=protein_tag,
                                        routing_="r",
                                        result_transformer_=Result.value,
                                    )

        return r


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


class Neo4JAnnotations(AnnotationsABC):

    def __init__(self, driver: Driver) -> None:
        self._driver = driver

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
        # query = (
        #     "MATCH (ag:AnnotationGroup {tag: $group_tag}) "
        #     "MERGE (a:Annotation {tag: $tag}) "
        #     "ON CREATE "
        #     "SET a.text = $text, "
        #     "    a.description = $description, "
        #     "    a.publication = $publication, "
        #     "    a.pubmed_id = $pubmed_id, "
        #     "    a.protein_tags = $protein_tags, "
        #     "    a.s = toLower($text)+' '+toLower($description), "
        #     "    a.created_at = timestamp() "
        #     "MERGE (ag)-[:HAS_ANNOTATION]->(a) "
        #     "RETURN TRUE"
        # )
        print("Inserting annotation:", annotation)
        query = (
            "MATCH (ag:AnnotationGroup {tag: $group_tag}) "
            "MERGE (a:Annotation {tag: $tag}) "
            "ON CREATE "
            "SET a.text = $text, "
            "    a.description = $description, "
            "    a.publication = $publication, "
            "    a.pubmed_id = $pubmed_id, "
            "    a.s = toLower($text)+' '+toLower($description), "
            "    a.created_at = timestamp() "
            "WITH a "
            "UNWIND $protein_tags AS protein_tag "
            "MATCH (p:Protein {tag: protein_tag}) "
            "MERGE (a)-[:ANNOTATES]->(p) "
            "MERGE (ag)-[:HAS_ANNOTATION]->(a) "
            "RETURN TRUE"
        )


        r = self._driver.execute_query( query,
                                        tag=annotation.tag,
                                        text=annotation.text,
                                        description=annotation.description,
                                        publication=annotation.publication,
                                        pubmed_id=annotation.pubmed_id,
                                        protein_tags=annotation.protein_tags,
                                        group_tag=annotation.group_tag,
                                        routing_="w",
                                        result_transformer_=Result.value,
                                    )

        return r[0] if r else False

    def get(self, tag: str) -> AnnotationsModel:
        
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
            raise Exception(f"Annotation not found")

        return AnnotationsModel(**r[0])


    def find(self, group_tag: Optional[str] = None, protein_tag: Optional[str] = None, search_string: Optional[str] = None) -> List[str]:
        
        

        if group_tag is not None:
            query = (
                "MATCH (:AnnotationGroup {tag: $group_tag})-[:HAS_ANNOTATION]->(a:Annotation) "
            )
        else:
            query = (
                "MATCH (a:Annotation) "
            )
        if protein_tag is not None:
            query = (
                "WHERE EXISTS {(a)-[:ANNOTTATES]->(p:Protein {tag = $protein_tag})} "
            )

        if search_string is not None:
            if protein_tag is not None:
                query += "AND "
            else:
                query += "WHERE "
            query += (
                "a.s CONTAINS $search_string "
                )


        query += "RETURN a.tag"

        r = self._driver.execute_query( query,
                                        tag=tag,
                                        group_tag=group_tag,
                                        protein_tag=protein_tag,
                                        search_string=search_string.lower() if search_string else None,
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
            "EXISTS {(:Annotation {tag: $tag})-[:ANNOTATES]->(p)} AS isin"
        )

        r = self._driver.execute_query( query,
                                        protein_ids=protein_ids,
                                        tag=tag,
                                        routing_="r",
                                        result_transformer_=Result.to_df,
        )

        if r.empty:
            return pd.Series([], dtype=bool)

        r = r.set_index("tag")
        return r["isin"]




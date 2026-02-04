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
            "    ag.created_by = u.email "
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
            " a.protein_tags = $protein_tags, "
            " a.modified_at = timestamp(), "
            " a.s = toLower($text)+' '+toLower(coalesce($description,'')) "
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
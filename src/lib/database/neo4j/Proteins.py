from neo4j import Driver, Result 
from typing import List, Dict
import pandas as pd 

from lib.database.abstract.Proteins import ProteinsABC

from config.settings.proteomes.annotations import UniprotAnnotationSettings

from config.models.annotations.feature import FeatureModel
from config.models.calculations.quantile import QuantileModel 

from services.annotations.uniprot import download_proteome_annotations
from config.models.feature import FeatureNeoModel, FeatureSequenceResponseModel



class Neo4JProteins(ProteinsABC):
    
    def __init__(self, driver : Driver) -> None:
        self._driver = driver 
        
    def count(self, quantified: bool = True) -> int:
        "Returns the number of quantified proteins in the database"
        if quantified:
            query = (
                "MATCH (:Sample)-[:QUANTIFIED]->(:ProteinGroup)-[:HAS_PROTEINS]->(p:Protein) "
                "RETURN count(DISTINCT p) "
            )
        else:
            query = (
                "MATCH (p:Protein) "
                "RETURN count(p) "
            )
        r = self._driver.execute_query(query, routing_="r", result_transformer_=Result.value)
        return r[0]
    
    
    def exists(self, tag: str) -> bool:
        query = (
            "WITH EXISTS {(p:Protein {tag : $tag})} as protein_exists "
            "RETURN protein_exists "
        )    
        r = self._driver.execute_query(query, tag = tag, result_transformer_=Result.value)
        return r[0]
    
    
    def find(self, search_string : str = None, submission_tags : List[str] = None, proteome_tags : List[str] = None, is_condition_value : bool = False, limit : int = 100) -> List[str]:
        ""
        where_conditions = []
        query = "MATCH (p:Protein) "
        
        if submission_tags is not None and len(submission_tags) > 0:
            where_conditions.append("EXISTS {(p)<-[:HAS_PROTEINS]-(pg:ProteinGroup)<-[:QUANTIFIED]-(:Sample)<-[:HAS_SAMPLE]-(submission:Submission) WHERE submission.tag IN $submission_tags}")
        if search_string is not None:
            where_conditions.append("p.s CONTAINS $search_string")
        if proteome_tags is not None and len(proteome_tags) > 0:
            where_conditions.append("p.proteome_tag IN $proteome_tags")
        if is_condition_value:
            where_conditions.append("EXISTS {(cv:ConditionValue)-[:EFFECTS]->(p)}")
        if where_conditions:
            query += "WHERE " + " AND ".join(where_conditions) + " "
        
        query += (
            "RETURN p.tag as tag "
            "ORDER BY COUNT { (p)--() } DESC "
        )
        if limit is not None:
            query += "LIMIT $limit"
        r = self._driver.execute_query(query, search_string = search_string.lower() if search_string is not None else None, proteome_tags = proteome_tags, submission_tags = submission_tags, limit = limit, routing_="r", result_transformer_=Result.value)

        return r
    
    def get(self, tag : str) -> FeatureNeoModel:
        ""
    
        query = (
            "MATCH (p:Protein) "
            "WHERE p.tag = $tag "
            "RETURN properties(p) as props " 
        )
        r = self._driver.execute_query(query, tag = tag, routing_="r", result_transformer_=Result.value)

        return FeatureNeoModel(**r[0])
  
    def get_favorite_proteins(self, submission_tags : List[str] = None, annotation_tags : List[str] = None, proteome_tags : List[str] = None, user_tag : str = None, limit : int = 40) -> List[str]:
        ""
        where_conditions = []
        score_conditions = []

        query = "MATCH (p:Protein) "

        # -------------------------
        # FILTER CONDITIONS
        # -------------------------

        if submission_tags:
            where_conditions.append(
                """
                EXISTS {
                    (p)<-[:HAS_PROTEINS]-(pg:ProteinGroup)
                        <-[:QUANTIFIED]-(:Sample)
                        <-[:HAS_SAMPLE]-(submission:Submission)
                    WHERE submission.tag IN $submission_tags
                }
                """
            )

        if annotation_tags:
            where_conditions.append(
                """
                EXISTS {
                    (p)<-[:ANNOTATES]-(a:Annotation)
                    WHERE a.tag IN $annotation_tags
                }
                """
            )

        if proteome_tags:
            where_conditions.append(
                """
                EXISTS {
                    (p)-[:IN_PROTEOME]->(pr:Proteome)
                    WHERE pr.tag IN $proteome_tags
                }
                """
            )

        if where_conditions:
            query += "WHERE " + " AND ".join(where_conditions) + " "

        # -------------------------
        # SCORE CONDITIONS
        # -------------------------

        if user_tag is not None:
            #favouring this condition with a high score to ensure that favored proteins are ranked higher than non-favored ones, even if they don't meet any of the other criteria
            score_conditions.append(
                """
                CASE
                    WHEN EXISTS {
                        (p)<-[:FAVOURS]-(:User {tag: $user_tag})
                    }
                    THEN 5 ELSE 0
                END
                """
            )

            score_conditions.append(
                """
                CASE
                    WHEN EXISTS {
                        (p)<-[:EFFECTS]-(:Genotype)
                            <-[:CREATED]-(:User {tag: $user_tag})
                    }
                    THEN 1 ELSE 0
                END
                """
            )

        # -------------------------
        # RETURN
        # -------------------------

        if score_conditions:
            score_expression = " + ".join(score_conditions)
        else:
            score_expression = "0"

        query += f"""
        RETURN
            p.tag AS tag,
            ({score_expression}) AS condition_count
        ORDER BY condition_count DESC
        """

        if limit is not None:
            query += "LIMIT $limit"

        r = self._driver.execute_query(
            query,
            submission_tags=submission_tags,
            annotation_tags=annotation_tags,
            user_tag=user_tag,
            limit=limit,
            routing_="r",
            result_transformer_=Result.value
        )

        return r
    
    
    
    def get_gene_name(self, tag : str) -> str:
        query = (
            "MATCH (p:Protein {tag : $tag}) "
            "RETURN p.gene_name AS gene_name "
        )
        r = self._driver.execute_query(query, tag = tag, routing_="r", result_transformer_=Result.value)
        return r[0] if len(r) > 0 else None
    
    
    def is_protein_favorite(self, protein_tag : str, user_tag : str) -> bool:
        ""
        query = (
            "MATCH (p:Protein {tag: $protein_tag}) "
            "RETURN EXISTS {(p)<-[:FAVOURS]-(:User {tag: $user_tag})} AS is_favorite"
        )
        r = self._driver.execute_query(query, protein_tag=protein_tag, user_tag=user_tag, routing_="r", result_transformer_=Result.value)
        return r[0] if len(r) > 0 else False
    
    def set_favorite_protein(self, protein_tag : str, user_tag : str) -> bool:
        ""
        query = (
            "MATCH (p:Protein {tag: $protein_tag}) "
            "MERGE (u:User {tag: $user_tag}) "
            "MERGE (u)-[f:FAVOURS]->(p) "
            "SET f.created_at = timestamp() "
            "RETURN f"
        )
        r = self._driver.execute_query(query, protein_tag=protein_tag, user_tag=user_tag, routing_="w", result_transformer_=Result.value)
        return len(r) > 0 and r[0] is not None
    
    def remove_favorite_protein(self, protein_tag : str, user_tag : str) -> bool:
        ""
        query = (
            "MATCH (u:User {tag: $user_tag})-[f:FAVOURS]->(p:Protein {tag: $protein_tag}) "
            "DELETE f "
            "RETURN COUNT(f) AS deleted_count"
        )
        r = self._driver.execute_query(query, protein_tag=protein_tag, user_tag=user_tag, routing_="w", result_transformer_=Result.value)
        return r[0] > 0 if len(r) > 0 else False
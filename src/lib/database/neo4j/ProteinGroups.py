from typing import Optional,List, Dict

from neo4j import Driver, Result

from lib.database.abstract.ProteinGroups import ProteinGroupsABC
from config.models.feature import ExclusivelyQuantifiedModel, ProteinGroupSubmissionStatisticsModel 

import pandas as pd 

class Neo4JProteinGroups(ProteinGroupsABC):
    
    def __init__(self, driver : Driver) -> None:
        ""
        self._driver = driver 
    
    
    def count(self, submission_tag : str) -> int:
        """Counts the number of protein groups. If a submission tag is given, only counts protein groups associated with that submission (e.g. that were quantified).
        """
        query = (
            "MATCH (submission:Submission {tag : $submission_tag})-[:HAS_SAMPLE]->(s:Sample)-[r:QUANTIFIED]->(pg:ProteinGroup) "
            "RETURN count(DISTINCT pg.tag)"
        )
        
        r = self._driver.execute_query(query, routing_="r", submission_tag = submission_tag, result_transformer_=Result.value)
        return r[0] if len(r) > 0 else 0
    
    
    def insert_bulk(self, protein_groups : List[str], protein_group_separator : str = ";") -> int:
        ""
        not_existing = [pg for pg in protein_groups if not self.exists(pg)]
        if len(not_existing) == 0: return 0
        query = (
            "UNWIND $protein_groups as group_tag "
            "WITH group_tag, split(group_tag, $protein_group_separator) as protein_tags "
            "MERGE (pg:ProteinGroup {tag: group_tag}) "
            "ON CREATE SET pg.created_at = timestamp() "
            "ON MATCH SET pg.modified_at = timestamp() "
            "WITH pg, protein_tags "
            "UNWIND protein_tags as protein_tag "
            "MATCH (p:Protein {tag: protein_tag}) "
            "MERGE (pg)-[:HAS_PROTEINS]->(p) "
        )
        r = self._driver.execute_query(query, routing_="w", protein_groups = not_existing, protein_group_separator = protein_group_separator)
        return len(not_existing)
    
    def exists(self, tag : str) -> bool:
        ""
        ""
        query = (
            "WITH EXISTS {(f:ProteinGroup {tag : $tag})} as group_exists "
            "RETURN group_exists "
        )    
        r = self._driver.execute_query(query, tag = tag, result_transformer_=Result.value)
        return r[0]
    
   
   
    def find(self, search_string : str = None, submission_tag : str = None, sort_by_stat_attribute : str = None,  annotation_tags : List[str] = None, limit : int = 20) -> List[str]:
        ""
        query = "MATCH (pg:ProteinGroup) "
        
        where_clauses = []
        if annotation_tags is not None and len(annotation_tags) > 0:
            where_clauses.append("""EXISTS {
                    MATCH (pg)-[:HAS_PROTEINS]->(:Protein)<-[:ANNOTATES]-(a:Annotation)
                    WHERE a.tag IN $annotation_tags
                        }""")
                        
            
            
        # Filter by submission first
        if submission_tag is not None:
                where_clauses.append("""
                                EXISTS {
                                MATCH (pg)<-[:QUANTIFIED]-(:Sample)<-[:HAS_SAMPLE]-
                                (:Submission {tag: $submission_tag})}
                                """)
        
        # Only expand proteins if search is needed
        if search_string is not None and search_string.strip() != "":


            where_clauses.append("""
                    (
                        toLower(pg.tag) CONTAINS $search_string
                        OR EXISTS {
                            MATCH (pg)-[:HAS_PROTEINS]->(p:Protein)
                            WHERE toLower(p.s) CONTAINS $search_string
                        }
                    )
                    """)
        
        if len(where_clauses) > 0:
            query += "WHERE " + " AND ".join(where_clauses) + " "

            
        if sort_by_stat_attribute is not None and submission_tag is not None:
             query += (
                "MATCH (pg)<-[:FOR_PROTEIN_GROUP]-(stats:Statistics) "
                "MATCH (stats)-[:OF_ATTRIBUTE]->(a:Attribute) "
                "WHERE a.tag = $sort_by_stat_attribute "
                "RETURN pg.tag AS tag, stats.score AS score "
                "ORDER BY score DESC "
             )
        else:
            query += "RETURN pg.tag AS tag " 

        if limit is not None:
            query += "LIMIT $limit"
            
        print(query)
            
        r = self._driver.execute_query(query, routing_="r", 
                                       search_string=search_string.lower() if search_string else None, 
                                       submission_tag=submission_tag, 
                                       sort_by_stat_attribute=sort_by_stat_attribute,
                                       annotation_tags=annotation_tags, 
                                       limit=limit, 
                                       result_transformer_=Result.data)
        print(r)
        return [ri["tag"] for ri in r]
    
    def get(self, tag : str):
        "" 
        
        query = (
            "MATCH (pg:ProteinGroup {tag : $tag})-[:HAS_PROTEINS]->(p:Protein) "
            "RETURN pg.tag as tag, pg.text as text, collect(p.tag) as protein_tags "
        )
        
        
        r = self._driver.execute_query(query, routing_="r", tag = tag, result_transformer_=Result.data)
        return r[0] if len(r) > 0 else None
    
    
    def get_proteins(self, tag : str) -> List[str]:
        "Returns the proteins in a specific protein group."
        
        query = (
            "MATCH (f:ProteinGroup {tag : $tag})-[:HAS_PROTEINS]->(p:Protein) "
            "RETURN p.tag as protein_tag "
        )
        
        r = self._driver.execute_query(query, routing_="r", tag = tag, result_transformer_=Result.value)
        return r
    
    def insert(self, protein_tags : List[str], tag : str, text : str) -> bool:
        ""
        if self.exists(tag): raise ValueError(f"Protein group with tag {tag} already exists. Use the update function." )
        
        query = (
            "MERGE (pg:ProteinGroup {tag  : $tag }) "
            "ON CREATE SET pg.created_at = timestamp() "
            "ON MATCH SET pg.modified_at = timestamp() "
            "OPTIONAL MATCH (pg)-[r:HAS_PROTEINS]->(p:Protein) "
            "DELETE r "
            "WITH pg "
            "UNWIND $protein_tags as protein_tag "
            "MATCH (p:Protein {tag : protein_tag}) "
            "MERGE (pg)-[:HAS_PROTEINS]->(p) "
        )
        
        self._driver.execute_query(query, routing_="w", tag = tag, text = text, protein_tags = protein_tags)
        return True
    
    
    def delete(self, tag: str) -> bool:
        ""
        if not self.exists(tag): raise ValueError(f"Protein group with tag {tag} does not exist.")
        
        query = (
            "MATCH (pg:ProteinGroup {tag : $tag}) "
            "DETACH DELETE pg "
        )
        
        self._driver.execute_query(query, routing_="w", tag = tag)
        return True
    
    
    def get_statistical_ranking(self, tag : str, attribute_tags : Optional[List[str]] = None, submission_tag : str = None, limit : Optional[int] = 20) -> List[ProteinGroupSubmissionStatisticsModel]:
        ""
        if not self.exists(tag): raise ValueError(f"Protein group with tag {tag} does not exist.")
        
        query = (
            "MATCH (pg:ProteinGroup {tag : $tag})<-[:FOR_PROTEIN_GROUP]-(stats:Statistics)-[:OF_ATTRIBUTE]->(a:Attribute) "
            "WHERE a.tag IN $attribute_tags OR $attribute_tags IS NULL "
            "MATCH (stats)<-[:HAS_STATS]-(submission:Submission) "
        )
        if submission_tag is not None:
            query += "WHERE submission.tag = $submission_tag "
        query += (    
            "RETURN stats.tag as tag, a.tag as attribute_tag, stats.mean as mean, stats.F as F, stats.rank as rank, stats.FDR as FDR, stats.exclusively_ca_tags  "
            "as exclusively_ca_tags, stats.p_value as p_value, stats.eta_squared as eta_squared, stats.cohen_f as cohen_f, stats.quantified_in_samples as quantified_in_samples, stats.max_fc as max_fc, stats.std_means as std_means, stats.missingness as missingness, stats.n_groups as n_groups, stats.score as score, stats.exclusively as exclusively, submission.tag as submission_tag "
            "ORDER BY stats.score DESC "
        )
        if limit is not None:
            query += "LIMIT $limit"
        
        r = self._driver.execute_query(query, routing_="r", tag = tag, attribute_tags = attribute_tags, limit=limit, result_transformer_=Result.data)
        return [ProteinGroupSubmissionStatisticsModel(**ri) for ri in r]
    
    def get_exclusively_quantified(self, submission_tag : str ) -> List[ExclusivelyQuantifiedModel]:
        
        
        query = (
            "MATCH (pg:ProteinGroup)<-[:FOR_PROTEIN_GROUP]-(stats:Statistics)-[:OF_ATTRIBUTE]->(a:Attribute)  " 
            "WHERE EXISTS {(stats)-[:HAS_STATS]-(submission:Submission {tag : $submission_tag})} AND stats.exclusively = true "
            "RETURN pg.tag as tag, a.tag as attribute_tag, stats.tag as stats_tag, stats.mean as mean, stats.exclusively_ca_tags as exclusively_ca_tags, stats.quantified_in_samples as quantified_in_samples ORDER BY mean DESC "
        )
        
        r = self._driver.execute_query(query, routing_="r", submission_tag = submission_tag, result_transformer_=Result.data)
        return sorted([ExclusivelyQuantifiedModel(**ri) for ri in r], key=lambda x: ";".join(x.exclusively_ca_tags), reverse=True)
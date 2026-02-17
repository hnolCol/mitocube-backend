

from neo4j import Driver, Result
from typing import List

class Annotations():
    
    
    
    
    def count_proteins_with_annotation(self, tag : str, submission_tag : str, protein_group_tags : List[str]) -> int:
        "Counts the number of proteins with the given annotation tag."
        "If a submission tag is provided, only proteins associated quantified in the submission are counted."
        "If protein_tags is provided, only proteins in the list are considered. This should be used when you want to count only among a subset of proteins such as the significantly changing ones."
        
        
        query = (
            "MATCH (a:Annotation {tag : $tag})-[:ANNOTATES]->(p:Protein) "
        )
        
        if submission_tag is not None:

            query += (
                "MATCH (s:Submission {tag : $submisssion_tag}) "
                "WHERE EXISTS {(s)-[:HAS_SAMPLE]-(s:Sample)-[:QUANTIFIED]-(pg:ProteinGroup)"
            )
            
            if protein_group_tags is not None and len(protein_group_tags) > 0:
                query += (
                    "WHERE pg.tag IN $protein_group_tags} "
                )
            else:
                query += (
                    "} "
                )
        
        if protein_group_tags is not None and len(protein_group_tags) > 0 and submission_tag is None:
            query += (
                "WHERE EXISTS {(p)-[:HAS_PROTEIN]-(pg:ProteinGroup) WHERE pg.tag in $protein_group_tags} "
            )
        
        
        
        r = self._driver.execute_query(query, routing_="r", tag=tag, result_transformer_=Result.value, protein_group_tags = protein_group_tags, submission_tag = submission_tag)
        return r[0] if len(r) > 0 else 0"
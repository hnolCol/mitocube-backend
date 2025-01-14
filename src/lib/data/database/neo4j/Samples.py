from typing import List, Tuple, Literal
from neo4j import Driver, Result

from lib.data.database.abstract.Samples import SamplesABC



class Neo4JSamples(SamplesABC):
    "" 
    def __init__(self, driver : Driver):
        
        self._driver = driver 
    
    def exists(self, tag : str) -> bool:

        
        query = (
            "WITH EXISTS {(s:Sample {tag : $tag})} as exists "
            "RETURN exists"
        )
        
        r = self._driver.execute_query(query,routing_="r",result_transformer_=Result.value, tag = tag)
        return r[0]
    
    def count(self, trait_tag : str) -> int:
        "Counts the number of samples"
        
        if trait_tag is not None:
            query = (
                "MATCH (s:Sample)<-[:HAS_SAMPLE]-(submission:Submission)-[:HAS_ATTRIBUTE_VALUE]->(trait:AttributeValue) "
                "WHERE trait.tag = $trait_tag "
                "RETURN count(s) as count"
            )
        else:
            query = (
                "MATCH (s:Sample) "
                "RETURN count(s) as count"
            )
        
        r = self._driver.execute_query(query, routing_="r", result_transformer_=Result.data, trait_tag = trait_tag)
        return r[0]["count"] 
        
        
    def get_samples_by_genotype(self, genotype_tag : str):
        "" 
        query = (
            "MATCH (s:Sample)-[:HAS_GENOTYPE]->(g:Genotype) "
            "WHERE g.tag = $genotype_tag "
            "RETURN s.tag as tag, g.tag as genotype_tag "
        )
        
        r = self._driver.execute_query(query, routing_="r", result_transformer_=Result.data, genotype_tag=genotype_tag)
        return r 

    def get_sample(self, tag : str):
        "Returns a sample an its trait as well genotype annotation."
        query = (
            "MATCH (s:Sample {tag : $tag})-[:HAS_SAMPLE]-(submission:Submission) " 
            "OPTIONAL MATCH (s)-[:HAS_GENOTYPE]->(g:Genotype) "
            "OPTIONAL MATCH (s)-[:HAS_SAMPLE_ATTRIBUTE_VALUE]->(trait:AttributeValue)"
            "RETURN s.tag as tag, g.tag as genotype_tag, trait.tag as trait_tag, submission.tag as submission_tag "
        )
        
        r = self._driver.execute_query(query,routing_="r",result_transformer_=Result.data, tag = tag)
        return  r 
    
    
    
    
    
    
    
    
    

from typing import List, Tuple, Literal
from neo4j import Driver, Result

from lib.database.abstract.Samples import SamplesABC



class Neo4JSamples(SamplesABC):
    "" 
    def __init__(self, driver : Driver):
        
        self._driver = driver 
    
    def exists(self, tag : str) -> bool:
        "Check if a sample is associated with the given tag."
        
        query = (
            "WITH EXISTS {(s:Sample {tag : $tag})} as exists "
            "RETURN exists"
        )
        
        r = self._driver.execute_query(query,routing_="r",result_transformer_=Result.value, tag = tag)
        return r[0]
    
    def count(self, trait_tag : str = None) -> int:
        
        "Counts the number of samples. If a specific trait tag is provided, the number of samples with a trait will be counted."
        
        if trait_tag is not None:
            query = (
                "MATCH (s:Sample)<-[:HAS_SAMPLE]-(submission:Submission)-[:HAS_ATTRIBUTE_VALUE]->(trait:Trait) "
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
        
        
    def insert(self, tag : str, submission_tag : str, sample_name : str, sample_index : int, trait_tags : List[str]):
        "Insert a new sample to a given submission" 
        if self.exists(tag = tag): raise ValueError("Sample tag exists already. ")
        
        
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
    
    
    
    
    def get_sample_string(self, tag : str) -> str:
        """Return a string for sample that describes the traits for a given sample. 
        This should be used to either visualize the sample in the gui. Or to access
        statistics as the string will be explicit for the trait/attributes"""
        
        query = (
            "MATCH (ca:ConditionApplication)-[]-(s:Sample {tag : $tag}) " 
            "CALL apoc.path.expand(ca, 'HAS_VALUE|HAS_UNIT|HAS_CHILD>', null, 1, 10) YIELD path "
            "WITH path "
            "WITH nodes(path) AS nodelist, length(path) AS depth "

            "WITH [x IN nodelist WHERE x:Trait OR x:ConditionValue | x.tag] AS tags, depth "

            "ORDER BY depth DESC "

            "WITH collect(tags) AS tagpaths "

            "WITH [tp IN tagpaths | "
            "reduce(output = "", tag IN reverse(tp) | "
            "   CASE output "
            "    WHEN "" THEN tag "
            "    ELSE tag + '(' + output + ')' "
            "    END) "
            "] AS nestedStrings "

            "RETURN nestedStrings "

            )
        
        r = self._driver.execute_query(query, routing = "r", result_transformer_=Result.value, tag = tag)
        print(r)
        
        return r 
    
    
    
    
    
    
    

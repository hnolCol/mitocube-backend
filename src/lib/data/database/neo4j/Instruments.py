from neo4j import Driver, Result 
from typing import List, Dict
import pandas as pd 

from lib.data.database.abstract.Instruments import InstrumentsABC



class Neo4JInstruments(InstrumentsABC):
    
    def __init__(self, driver : Driver) -> None:
        self._driver = driver 
        
        
        
    def get(self, tags: List[str] = None) -> List:
        
        query = (
            "MATCH (av:AttributeValue)-[:HAS_VALUE]-(a:Attribute) "
            "WHERE a.tag = 'att_ms' "
            )
        
        if tags is not None:
            query += "AND av.tag in $tags "
            
        query += "RETURN properties(av) "
        
        r = self._driver.execute_query(query, routing_="r", result_transformer_=Result.values, tags=tags)
        
        print(r)
        return r 
        
    def get_samples_by_instrument(self, tags: List[str]) -> Dict:
        ""
        
        query = (
            "MATCH (av:AttributeValue) "
            "WHERE av.tag in $tags "
            "MATCH (av)<-[:HAS_ATTRIBUTE_VALUE]-(submission:Submission)-[:HAS_SAMPLE]->(sample:Sample) "
            "WHERE EXISTS {(sample)-[:QUANTIFIED]->(:Protein)} "
            "RETURN av.tag as instrument_tag, submission.tag as submission_tag, count(sample) as sample_count"
        )
        
        r = self._driver.execute_query(query, routing_="r", result_transformer_=Result.data, tags=tags)
        
        print(r)
        return r 
        
        
    def get_counts_by_instrument_and_attribute(self, attribute_tags : List[str], tags : List[str] = None):
        "" 
        query = (
            "MATCH (instrument:AttributeValue)-[:HAS_VALUE]-(a:Attribute) "
            "WHERE a.tag = 'att_ms' "
        )
        
        if tags is not None:
            query += "AND instrument.tag in $tags "
            
        query += (
            "MATCH (instrument)<-[:HAS_ATTRIBUTE_VALUE]-(submission:Submission) "
            "MATCH (submission)-[:HAS_VALUES_FOR_ATTRIBUTE]->(a2:Attribute)-[:HAS_VALUE]->(av:AttributeValue) "
            "WHERE a2.tag in $attribute_tags "
            "MATCH (submission)-[:HAS_SAMPLE]->(sample:Sample) "
            "RETURN instrument.tag as instrument_tag, a2.tag as attribute_tag, av.tag as trait_tag, submission.tag as submission_tag, count(sample) as sample_count "
        )
        
        
        r = self._driver.execute_query(query, routing_="r",result_transformer_=Result.data, tags = tags, attribute_tags = attribute_tags)
        
        print(r)
        
        
        return r 
from neo4j import Driver, Result 
from typing import List, Dict
import pandas as pd 

from lib.database.abstract.Instruments import InstrumentsABC



class Neo4JInstruments(InstrumentsABC):
    
    def __init__(self, driver : Driver) -> None:
        self._driver = driver 
        
    def get_types(self, limit : int = 50) -> List[str]:
        "Returns all the instrument type tags"
        query = (
            "MATCH (it:InstrumentType) RETURN it.tag LIMIT 50"
        )
        
        instrument_types = self._driver.execute_query(query, routing_="r",result_transformer_=Result.value, limit = limit)
        
        return instrument_types
        
        
    def get(self, instrument_type : str = None, tags: List[str] = None) -> List:
        """An instrument is a trait, but the attribute has a label that is 
        Instrument. In addition there are instrument types (e.g. mass spec type, lc type)
        that group the instruments. 
        Hence you can provide a type go get the list of instrument tags (Traits). 
        If no instrument_type is provided, all instrument tags will be returned. 

        Parameters
        ----------
        instrument_type : str, optional
            _description_, by default None
            
        Returns
        -------
        List
            Instrument tags
        """
        
        query = (
            "MATCH (i:Instrument) "
        )
        
        if instrument_type is not None:
            query += "WHERE EXISTS {(it:InstrumentType {tag : $instrument_type})-[:IS_CHILD]->(i)} "
        
        query += "MATCH (i)-[:HAS_TRAIT]->(t:Trait) RETURN t.tag "

        
        r = self._driver.execute_query(query, routing_="r", result_transformer_=Result.value, instrument_type = instrument_type)
        print(r,"GET INSTRUMENT TYPE!")
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
            "MATCH (submission)-[:HAS_VALUES_FOR_ATTRIBUTE]->(a2:Attribute)-[:HAS_TRAIT]->(av:Trait) "
            "WHERE a2.tag in $attribute_tags "
            "MATCH (submission)-[:HAS_SAMPLE]->(sample:Sample) "
            "RETURN instrument.tag as instrument_tag, a2.tag as attribute_tag, av.tag as trait_tag, submission.tag as submission_tag, count(sample) as sample_count "
        )
        
        
        r = self._driver.execute_query(query, routing_="r",result_transformer_=Result.data, tags = tags, attribute_tags = attribute_tags)
        
        return r 
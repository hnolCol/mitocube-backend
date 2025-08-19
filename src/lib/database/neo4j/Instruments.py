from neo4j import Driver, Result 
from typing import List, Dict
import pandas as pd 
from services.random_generators import get_random_string
from config.models.instruments import InstrumentStateModel, InstrumentsStateResponseModel, InstrumentStateHistoryModel

from lib.database.abstract.Instruments import InstrumentsABC
from lib.database.abstract.Instruments import InstrumentStatesABC



class Neo4JInstrumentStates(InstrumentStatesABC):
    
    def __init__(self, driver : Driver) -> None:
        self._driver = driver 
    
    def _utils_insert_from_file(self, file_path : str =  "/Users/hnolte/Documents/GitHub/mitocube-backend/resources/maintenance/instrumentstates.txt", *args, **kwargs):
        
        instrument_states = pd.read_csv(file_path, *args, **kwargs)
        if not all(column_name in instrument_states.columns for column_name in ["tag","text","description","color"]):
            raise ValueError("The dataframe does not have all required columns. 'tag','text','description','color'")
        
        instrument_state_models = [InstrumentStateModel(**i) for i in instrument_states.to_dict(orient="records")]
        query = (
            "UNWIND $states as is_props "
            "MERGE (is:InstrumentState {tag : is_props.tag}) "
            "ON CREATE "
            "SET is.description = is_props.description, is.text = is_props.text, is.color = is_props.color, is.created_at = timestamp() "
            "ON MATCH "
            "SET is.description = is_props.description, is.text = is_props.text, is.color = is_props.color, is.modified = timestamp() "
            "RETURN count(is) "
        )
        
        r = self._driver.execute_query(query,routing_="w", states = [i_state.model_dump() for i_state in instrument_state_models])
        print(r,"Instrument States created.")
        
    def get(self, tag = None) -> InstrumentStateModel:
        ""
        
        query = (
            "MATCH (is:InstrumentState {tag : $tag}) "
            "RETURN {tag : is.tag, text : is.text, description : is.description, color : is.color} "
        )
        r = self._driver.execute_query(query, tag = tag, routing_="r", result_transformer_=Result.value)
        return InstrumentStateModel(**r[0])
        
    def get_instrument_state(self, instrument_tag : str, limit : int = 1) -> List[InstrumentsStateResponseModel]:
        "Returns the state "
            
        query = (
            "MATCH (instrument:Trait {tag : $instrument_tag})<-[:HAS_TRAIT]-(a:Attribute) WHERE EXISTS {(a)-[:PART_OF]->(ag:AttributeGroup {tag : 'instrument'})} "
            "MATCH (instrument)-[r:IN_STATE]-(is:InstrumentState) "
            "RETURN {tag : is.tag, comment : r.comment, created_at : r.created_at} ORDER BY r.created_at DESC "
        )
        
        if limit is not None:
            query += " LIMIT $limit"
            
        r = self._driver.execute_query(query,instrument_tag = instrument_tag, result_transformer_=Result.value, limit = limit)

        return [InstrumentsStateResponseModel(**ri) for ri in r]
    
    
    
    
    
    def get_state_durations(self, instrument_tag : str = None, state_tag : str = None, timestamp_min : float = None, timestamp_max : float = None, limit : int = None) -> List[InstrumentStateHistoryModel]:
        ""
        query = "MATCH (t:Trait)-[r:IN_STATE]->(state:InstrumentState) "
        if instrument_tag is not None:
            query += "WHERE t.tag = $instrument_tag "
        elif timestamp_max is not None or timestamp_min is not None:
            query += "WHERE "
        elif state_tag is not None:
            query += "WHERE state.tag = $state_tag "
        
        if timestamp_min is not None and timestamp_max is not None:
            query += (      
                "r.created_at >= $timestamp_min AND r.created_at <= $timestamp_max ")
        elif timestamp_min is not None:
            query += (      
            "r.created_at >= $timestamp_min ")
        elif timestamp_max is not None:
            query += (      
            "r.created_at <= $timestamp_max ")

            
        query += "WITH t, state, r.tag as tag, r.created_at AS created ORDER BY created ASC " 
        
        if limit is not None:
            query += " LIMIT $limit "
        
        query += (
            "WITH COLLECT({tag : tag, instrument_tag : t.tag, state : state.tag, created_at : created}) as l  "
            "WITH [idx IN range(0, size(l)-1) |  "
            "       { "
            "           tag : l[idx].tag, "
            "           started_at : l[idx].created_at, "
            "           ended_at : l[idx+1].created_at, "
            "           instrument_tag : l[idx].instrument_tag, "
            "           state_tag : l[idx].state, "
            "           duration : (l[idx+1].created_at-l[idx].created_at) "
            "       }] AS durations "
            "RETURN durations "
        )
        
        r = self._driver.execute_query(query, instrument_tag = instrument_tag, limit = limit, routing_= "r", result_transformer_=Result.value)
        
        return [InstrumentStateHistoryModel(**ri) for ri in r[0]]
    
    
    def find(self, search_string = None, limit : int = None) -> List[str]:
        
        query = "MATCH (is:InstrumentState)  " 
        
        if search_string is not None:
            query += "WHERE toLower(is.text) CONTAINS toLower($search_string) OR toLower(is.description) CONTAINS toLower($search_string) "
            
        query += "RETURN is.tag "
        
        if limit is not None:
            query += "LIMIT $limit "
            
        r = self._driver.execute_query(query, search_string = search_string, limit = limit, routing_="r", result_transformer_=Result.value) 
        return r 
        


    def insert(self, state):
        return super().insert(state)
    
    
    def set_state(self, tag : str, instrument_tag : str, comment : str = None):
        ""
        
        unique_tag = get_random_string(N = 10)
        
        query = (
            "MATCH (is:InstrumentState {tag : $tag}) "
            "MATCH (instrument:Trait {tag : $instrument_tag})<-[:HAS_TRAIT]-(a:Attribute) WHERE EXISTS {(a)-[:PART_OF]->(ag:AttributeGroup {tag : 'instrument'})} "
            "CREATE (is)<-[r:IN_STATE]-(instrument) "
            "SET r.created_at = timestamp(), r.comment = $comment, r.tag = $r_tag "
        )
        
        self._driver.execute_query(query, routing_="w", tag = tag, instrument_tag = instrument_tag, comment = comment, r_tag = unique_tag)
        

class Neo4JInstruments(InstrumentsABC):
    
    def __init__(self, driver : Driver) -> None:
        self._driver = driver 
        
    def get_types(self, limit : int = 50) -> List[str]:
        "Returns all the instrument type tags"
        query = (
            "MATCH (ag:AttributeGroup)<-[:PART_OF]-(a:Attribute) WHERE ag.tag = 'instrumenttype' RETURN a.tag LIMIT $limit"
        )
        
        instrument_types = self._driver.execute_query(query, routing_="r",result_transformer_=Result.value, limit = limit)
        
        return instrument_types
        
        
    def get(self, instrument_type : str = None, tags: List[str] = None) -> List:
        """An instrument is a trait of an attribute The attribute is in an AttributeGroup 'instrument'
        In addition there are instrument types (e.g. mass spec type, lc type)
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
            "MATCH (ag:AttributeGroup)<-[:PART_OF]-(a:Attribute) WHERE ag.tag = 'instrument' "
        )
        
        if instrument_type is not None:
            query += "AND EXISTS {(:AttributeGroup {tag : 'instrumenttype'})<-[:PART_OF]-(a_type:Attribute)-[:IS_CHILD]->(a) WHERE a_type.tag = $instrument_type} "
        
        query += "MATCH (a)-[:HAS_TRAIT]->(t:Trait) RETURN t.tag "

        
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
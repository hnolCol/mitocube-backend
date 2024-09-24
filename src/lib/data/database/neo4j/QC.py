from typing import List, Tuple, Literal
from neo4j import Driver, Result

from lib.data.database.abstract.QC import QCABC
from config.models.performance import QCRunModel



class Neo4JQC(QCABC):
    
    def __init__(self, driver : Driver) -> None:
        self._driver = driver 
        
    def delete(self, tag: str) -> bool:
        return super().delete(tag)
    
    def count(self, by_instrument: bool = False) -> int:
        return super().count(by_instrument)
    
    def exists(self, tag: str) -> bool:
        return super().exists(tag)
    
    
    def update(self, tag: str, peformance_run: QCRunModel) -> bool:
        return super().update(tag, peformance_run)
    
    def get(self, tags: List[str] = None, instrument_tag : str = None, limit: int = 50) -> QCRunModel:

        query = (
            "MATCH (qc:QCRun) "
        )
        
        if tags is not None: 
            query += "WHERE qc.tag in $tags "
            if instrument_tag is not None:
                query += "AND qc.instrument = $instrument_name_tag "
        
        elif instrument is not None:
            query += "WHERE qc.instrument = $instrument_name_tag "
            
        
        self._driver.execute_query(query, routing_="r", result_transformer_=Result.value) 
        
    def insert(self, performance_run: QCRunModel) -> bool:
        
        
        attribute_values  = [{"tag" : a_tag, "value" : av_tag} for a_tag, av_tags in performance_run.group_attr.items() for av_tag in av_tags]
        peptides = [{'tag' : peptide_tag, 'rt' : rt} for peptide_tag, rt in performance_run.rt_peptides.items()]

        query = (
            "MERGE (qc:QCRun {tag : $performance_run_props.tag}) "
            "SET qc += $performance_run_props "
            "SET qc.created_at = timestamp() "
            "WITH qc "
            "MATCH (a:Attribute {tag: 'att_ms_name'})-[:HAS_VALUE]->(ms_instrument:AttributeValue) "
            "WHERE ms_instrument.tag = $performance_run_props.instrument_name_tag " 
            "MERGE (ms_instrument)<-[:QUALITY_CHECKED]-(qc) "
            "WITH qc "
            "UNWIND $attribute_values as attribute_value "
            "MATCH (a:Attribute {tag : attribute_value.tag})-[:HAS_VALUE]->(lc_part:AttributeValue {tag : attribute_value.value}) "
            "MERGE (lc_part)<-[r:LC_MS_SYSTEM]-(qc) "
            "WITH qc "
            "UNWIND $peptides as peptide "
            "MERGE (pep:Peptide {tag : peptide.tag}) "
            "MERGE (pep)<-[r_rt:RT_CHECK]-(qc) "
            "SET r_rt.rt = peptide.rt, r_rt.created_at = timestamp() "
        )
        
        print(performance_run)
        
        r = self._driver.execute_query(query, routing_="w", result_transformer_=Result.value, 
                                       performance_run_props = performance_run.model_dump(exclude_none=True, exclude=["rt_peptides","group_attr"]),
                                       peptides = peptides,
                                       attribute_values = attribute_values)
        print(r)
        
        return True 
    

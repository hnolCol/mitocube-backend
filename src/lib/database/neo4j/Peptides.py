from typing import List, Dict
from neo4j import Driver, Result
import pandas as pd 

from lib.database.abstract.Peptides import PeptidesABC
from config.settings.proteomes.annotations import UniprotAnnotationSettings

from services.annotations.uniprot import download_proteome_annotations
from config.models.feature import FeatureNeoModel
from config.models.performance import QCPeptidesModel, QCPeptideModel


class Neo4JPeptides(PeptidesABC):
     
    def __init__(self, driver : Driver) -> None:
        ""
        self._driver = driver  
        
        
    def exists(self, tag: str) -> bool:
        return super().exists(tag)
    
    
    def set_qc_peptides(self, peptides: QCPeptidesModel, join : bool = True):
        
        query = "MERGE (qc:QCPeptide) "
        if not join:
            query += (
                "WITH qc "
                "MATCH (qcpep:Peptide)-[:IS]->(qc) "
                "DETACH DELETE qcpep "
                )
        
        query += (
            "WITH qc "
            "UNWIND $qcpeptides.peptides as qcpeptide "
            "MERGE (pep:Peptide {tag : qcpeptide.sequence}) "
            "SET pep += qcpeptide "
            "WITH qc, pep, qcpeptide "
            "MATCH (p:Protein {tag : qcpeptide.protein_tag}) "
            "MERGE (qc)<-[r:IS]-(pep)<-[:HAS]-(p) "
            "ON CREATE "
            "SET r.created_at = timestamp(), r.user_tag = qcpeptide.user_tag "
            "RETURN count(r)"
            )
            
        r = self._driver.execute_query(query, routing_="w", qcpeptides = peptides.model_dump(exclude_none=True), result_transformer_=Result.value)
        
        
    def get_qc_peptides(self) -> List[QCPeptideModel]:
        ""
        query = (
            "MATCH (qc:QCPeptide)-[IS]-(pep:Peptide) "
            "RETURN properties(pep)"
        )
        
        r = self._driver.execute_query(query, result_transformer_=Result.value, routing_="r")
        return [QCPeptideModel(**ri) for ri in r] 
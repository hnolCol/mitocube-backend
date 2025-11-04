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
                "MATCH (p:Protein) "
                "WHERE EXISTS {(p:Protein)<-[:QUANTIFIED]->(:Sample)}"
                "RETURN count(p) " 
            )
            
        else:
            query = (
                "MATCH (p:Protein) "
                "RETURN count(p) " 
            )
            
        r = self._driver.execute_query(query,routing_="r",result_transformer_=Result.value)
        return r[0]
    
    
    def exists(self, tag: str) -> bool:
        query = (
            "WITH EXISTS {(p:Protein {tag : $tag})} as protein_exists "
            "RETURN protein_exists "
        )    
        r = self._driver.execute_query(query, tag = tag, result_transformer_=Result.value)
        return r[0]
    
    
    def find(self, search_string : str = None, limit : int = 100) -> List[str]:
        ""
        query = "MATCH (p:Protein) "
        if search_string is not None:
            query += "WHERE p.s CONTAINS toLower($search_string) "
        query += (
            "RETURN p.tag as tag "
            "ORDER BY COUNT { (p)--() } DESC "
            "LIMIT $limit "
        )
        r = self._driver.execute_query(query, search_string = search_string, limit = limit, routing_="r", result_transformer_=Result.value)
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
  
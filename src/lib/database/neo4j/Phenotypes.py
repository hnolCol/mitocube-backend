from typing import Dict, List, Tuple, Literal
from neo4j import Driver, Result


from lib.database.abstract.Phenotypes import PhenotypeABC
from config.models.phenotype import PhenotypeInputModel, PhenotypeModel


class Neo4JPhenotypes(PhenotypeABC):
    
    def __init__(self, driver: Driver) -> None:
        self._driver = driver 
        
    def connect(self, tag: str, genotype_tag, attributes: Dict[str, List[str]]):
        ""
        connect_tag = "12318sd2"
        attribute_traits = [{"attribute_tag" : a, "trait_tag" : t} for a,ts in attributes.items() for t in ts]
        query = (
            "MATCH (p:Phenotype {tag $tag}) "
            "MATCH (g:Genotype {tag : $genotype_tag}) "
            "MERGE (p)<-[r:HAS]-(g) "
            "SET r.tag = $connect_tag "
            "UNWIND $attribute_traits as at "
            "MATCH (a:Attribute {tag: at.attribute_tag}) "
            "MATCH (t:Trait {tag: at.trait_tag}) "
            "MERGE (t)-[r_tp {tag : $connect_tag}:]->(p) "
            "ON CREATE "
            "SET r_tp.created_at = timestamp() "
            "ON MATCH "
            "SET r_tp.modified_at = timestamp() "
            
        )
        
        r = self._driver.execute_query(query, routing_="w", 
                                       genotype_tag = genotype_tag, 
                                       tag = tag, 
                                       attribute_traits = attribute_traits, 
                                       connect_tag = connect_tag,
                                       result_transformer_=Result.value)
        
        
    def count(self) -> int:
        
        query = (
            "MATCH (p:Phenotype) "
            "RETURN count(p) "
        )
        
        r = self._driver.execute_query(query,routing_="r",result_transformer_=Result.value)
        if len(r) < 1: return 0 
        return r[0]
        
    def find(self, query: str = None, limit: int = 20) -> List[PhenotypeModel]:
        ""
        cypher_query = (
            "MATCH (p:Phenotype) "
            "WHERE p.s CONTAINS $query "
            "RETURN properties(p) LIMIT $limit "
        )
        
        r = self._driver.execute_query(cypher_query, 
                                   routing_="r", 
                                   query = query.lower(),
                                   limit = limit, 
                                   result_transformer_=Result.value)
        return [PhenotypeModel(**ri) for ri in r]
        
    def get(self, tags: List[str] = None, limit: int = 20) -> List[PhenotypeModel]:
        
        query = (
            "MATCH (p:Phenotype) "
        )
        
        if tags is not None and len(tags) > 0:
            query += "WHERE p.tag IN $tags "
            
        query += "RETURN properties(p) LIMIT $limit "

        r = self._driver.execute_query(query, tags = tags, limit = limit, result_transformer_=Result.value)
        return [PhenotypeModel(**ri) for ri in r]
        
        
    def insert(self, phenotype: PhenotypeInputModel):

        query = (
            "MERGE (p:Phenotype {tag : $phenotype.tag}) "
            "ON CREATE "
            "SET p.created_at = timestamp(), p.text = $phenotype.text, "
            "   p.description = $phenotype.description, p.group_tag = $phenotype.group_tag, "
            "   p.group_text = $phenotype.group_text, p.s = toLower($phenotype.text)+' '+toLower($phenotype.description)+' '+toLower($phenotype.group_text) "
            "ON MATCH "
            "SET p.modified_at = timestamp(), p.text = $phenotype.text, "
            "   p.description = $phenotype.description, p.group_tag = $phenotype.group_tag, "
            "   p.group_text = $phenotype.group_text, p.s = toLower($phenotype.text)+' '+toLower($phenotype.description)+' '+toLower($phenotype.group_text) "
            )
        
        self._driver.execute_query(query, routing_="w",phenotype = phenotype.model_dump(exclude_none=True))
        
        
        
        
        
    
        
        
from typing import List, Dict
from neo4j import Driver, Result
import pandas as pd 

from lib.data.database.abstract.Proteomes import ProteomesABC
from config.settings.proteomes.annotations import UniprotAnnotationSettings

from services.annotations.uniprot import download_proteome_annotations
from config.models.feature import FeatureNeoModel


class Neo4JProteomes(ProteomesABC):
     
    def __init__(self, driver : Driver) -> None:
        ""
        self._driver = driver    
        
    def add_proteome_details(self, proteome_tag : str, proteome_info : Dict):
        ""
        #trim proteome_info 
        for attr in ["reference","genomeAssembly","dbReference","component",'annotationScore','scores','redundantProteome']:
            if attr in proteome_info:
                del proteome_info[attr]
        if "name" in proteome_info and "description" in proteome_info:
            proteome_info["text"] = proteome_info["name"]
            proteome_info["s"] = f"{proteome_tag} {proteome_info['description']} {proteome_info['name']}"
        
        proteome_info["attribute_tag"] = "att_proteome"
        
        query = (
            "MERGE (av:AttributeValue {tag : $proteome_tag}) "
            "ON CREATE "
            "SET av.created_at = timestamp() "
            "ON MATCH "
            "SET av.modified_at = timestamp() "
            "WITH av "
            "SET av += $proteome_info "
            "WITH av "
            "MATCH (a:Attribute {tag : 'att_proteome'}) "
            "MERGE (a)-[:HAS_VALUE]->(av) "
            "RETURN av"
            
        ) 
        
        self._driver.execute_query(query, proteome_tag = proteome_tag, proteome_info = proteome_info)
        print("done")
        
    def count(self) -> int:
        query = (
            "MATCH (a:Attribute {tag : 'att_proteome'})-[:HAS_VALUE]->(av:AttributeValue) "
            "RETURN count(av) "
        )
        r = self._driver.execute_query(query_=query,routing_="r",result_transformer_=Result.value)
        return r 
    
    def delete(self, tag: str) -> bool:

        query = (
            "MATCH (av:AttributeValue {tag : $proteome_tag}) "
            "SET av.active = false "
            )
        try:
            self._driver.execute_query(query_=query,routing_="w")
            return True
        except Exception as e:
            print(e)
            return False 
        
        

    
    def exist(self, tags : str|List[str]) -> bool:
        """Check if tag/tags exists. If list is given,
        then it checks if ALL exist. If one is missing, 
        False will be returned. 

        Parameters
        ----------
        tags : List[str]
            _description_

        Returns
        -------
        bool
            If all given tags exists
        """
        
        if isinstance(tags,str):
            tags = [tags]
        
        query = ("MATCH (a:Attribute {tag : 'att_proteome'})-[:HAS_VALUE]->(av:AttributeValue) "
                 "WHERE av.tag in $tags "
                 "RETURN av.tag "
                 )
        
        r = self._driver.execute_query(query,routing_="r",result_transformer_= Result.value, tags = tags)
        
        return len(r) == len(tags)
    
    def find_features(self, query: str, proteome_tags: str | List[str] = None, limit: int = 10) -> List:
        ""
        if proteome_tags is None:
            cypher_query = (
                "MATCH (p:Protein) "
                "WHERE p.s CONTAINS $query_string "
                "RETURN collect(properties(p))[0..$limit] " 
            )
            
        else:
            if isinstance(proteome_tags,str):
                proteome_tags = [proteome_tags]
            
            proteome_tags_exist = self.exist(tags=proteome_tags)
            if not proteome_tags_exist: raise ValueError("Not all of the given proteome tags exist.")
            
            cypher_query = (
                "MATCH (p:Protein) "
                "WHERE p.s CONTAINS $query_string AND p.proteome_tag in $proteome_tags "
                "RETURN collect(properties(p))[0..$limit] " 
            )
        try:
            r = self._driver.execute_query(cypher_query, 
                                        database_="neo4j", 
                                        routing_="r", 
                                        result_transformer_= Result.value,
                                        query_string = query.lower(),
                                        proteome_tags = proteome_tags,
                                        limit = limit)
        except Exception as e:
            print("Query finding resulted in an error " + str(e))
            return []
        return [FeatureNeoModel(**f) for f in r[0]]
               
        
    
    def get(self) -> List[Dict]:
        ""
        
        query = (
            "MATCH (a:Attribute {tag : 'att_proteome'})-[:HAS_VALUE]->(av:AttributeValue) "
            "RETURN properties(av) "
        )
        
        r = self._driver.execute_query(query,routing_="r",database_="neo4j", result_transformer_= Result.value)
        return [ri for ri in r]

    def get_features(self, tag: str) -> List[FeatureNeoModel]:
        
        query = (
            "MATCH (av:AttributeValue {tag : $tag) "
            "(av)<-[r:IN_PROTEOME]->(p:Protein) "
            "RETURN properties(p)"
        )
        
        r = self._driver.execute_query(query_=query,routing_="r")
        return [FeatureNeoModel(**d.data()) for d in r]
    

    def insert_uniprot_proteome(self, proteome_tags : List[str] = ["UP000005640"], reviewed : bool = True, user_tag : str = None) -> int: #:#"):#"file:///UP000005640.txt"):#
        
        settings = UniprotAnnotationSettings()
        uniprotKB_URL = settings.uniprotKBAPI_URL
        
        return download_proteome_annotations(uniprotKB_URL,proteome_tags,
                                             chunc_callback=self.handle_uniprot_chunc, 
                                             add_proteome_callback=self.add_proteome_details, 
                                             reviewed = reviewed,
                                             user_tag = user_tag)
        
    def handle_uniprot_chunc(self,data : pd.DataFrame, proteome_tag : str, user_tag : str = None):
        """Data from the Uniprot API are returned in several pages covering
        500 entries. This function handles the chuncks and inserts the entries into the database. 
        

        Parameters
        ----------
        data : pd.DataFrame
            _description_
        proteome_tag : str
            _description_
        user_tag : str, optional
            The user that added the proteome identified by its tag, by default None
        """
        self._insert_uniprot_db(data,proteome_tag,user_tag=user_tag)

    
    def _insert_uniprot_db(self, data : pd.DataFrame, proteome_tag : str = "UP000005640", user_tag : str = None): 
        """Insert data from a Uniprot reference proteome to the database. 

        Parameters
        ----------
        data : pd.DataFrame
            The protein data with the following headers
            
                - Length (int) : The number of amino acids
                - Gene names (str) : All gene names associated with the protein
                - Gene Names (primary) (str)
                - Protein Names (str) - The associated protein name 
                - Entry (str) : The Uniprot ID 
                - Sequence (str) : The protein sequence.
                
        proteome_tag : str, optional
            The Uniprot reference proteome ID, by default "UP000005640" (Human)
        user_tag : str, optional
            The tag associated with a user, by default None
        """
        
        query = (
            "UNWIND $uniprot_features as row "
            "MERGE (n:Protein:AttributeValue {tag : row.Entry}) "
            "ON CREATE "
            " SET n += {aa_length : row.Length, gene_name : row.`Gene Names (primary)`, gene_names : row.`Gene Names`, protein_name : row.`Protein names`, created_at : timestamp(), proteome_tag : $proteome_tag, s : toLower(row.`Gene Names`)+' '+toLower(row.Entry)+' '+toLower(row.`Protein names`), viewed : 0} "
            "ON MATCH "
            " SET n.gene_names = row.`Gene Names`, n.protein_name = row.`Protein names`, n.gene_name = row.`Gene Names (primary)`, n.aa_length = row.Length, n.proteome_tag = $proteome_tag "
            "WITH n, row "
            "MERGE (av:AttributeValue {tag : $proteome_attribute_tag}) "
            "ON CREATE "
            "SET av.created_at = timestamp(), av.user_tag = $user_tag "
            "ON MATCH "
            "SET av.modified_at = timestamp(), av.user_tag = $user_tag "
            "WITH n,av, row "
            "MERGE (n)-[r:IN_PROTEOME]->(av) "
            "MERGE (sequence:Sequence {content : row.Sequence, version : row.`Sequence version`}) "
            "MERGE (n)-[:HAS_SEQUENCE]-(sequence) "
        )
        self._driver.execute_query(query, 
                                   proteome_attribute_tag = proteome_tag, 
                                   uniprot_features = data.to_dict(orient="records"), 
                                   proteome_tag = proteome_tag,
                                   user_tag = user_tag,
                                   routing_="w",
                                   database_="neo4j")
        
        print("Page added to database ...")
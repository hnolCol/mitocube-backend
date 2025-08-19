from typing import List, Dict
from neo4j import Driver, Result
import itertools
import pandas as pd 
import numpy as np 
from lib.database.abstract.Proteomes import ProteomesABC
from config.settings.proteomes.annotations import UniprotAnnotationSettings

from lib.database.abstract.Features import FeaturesABC
from services.annotations.uniprot import download_proteome_annotations
from config.models.feature import FeatureNeoModel
from config.models.calculations.quantile import QuantileModel


class Neo4JProteomes(ProteomesABC):
     
    def __init__(self, driver : Driver, features : FeaturesABC) -> None:
        ""
        self._driver = driver    
        self._features = features 
                
    def add_proteome_details(self, proteome_tag : str, proteome_info : Dict):
        ""
        #trim proteome_info 
        for attr in ["reference","genomeAssembly","dbReference","component",'annotationScore','scores','redundantProteome']:
            if attr in proteome_info:
                del proteome_info[attr]
        if "name" in proteome_info and "description" in proteome_info:
            proteome_info["text"] = proteome_info["name"]
            proteome_info["s"] = f"{proteome_tag} {proteome_info['description']} {proteome_info['name']}"
                
        query = (
            "MERGE (proteome:Proteome {tag : $proteome_tag}) "
            "ON CREATE "
            "SET proteome.created_at = timestamp(), proteome.active = true  "
            "ON MATCH "
            "SET proteome.modified_at = timestamp() "
            "WITH proteome "
            "SET proteome += $proteome_info "
        ) 
        
        self._driver.execute_query(query, proteome_tag = proteome_tag, proteome_info = proteome_info)
        return True
    
    
        
    def count(self) -> int:
        query = (
            "MATCH (prot:Proteome) "
            "RETURN count(prot) "
        )
        r = self._driver.execute_query(query_=query,routing_="r",result_transformer_=Result.value)
        if len(r) == 0: return 0
        return r[0]
        return r 
    
    def correlate_features(self, tag : str, cutoff : float = 0.5, min_data_points : int = 20, chunk_size : int = 20000):
        "Correlates each feautre."
        feature_tags = self.get_feature_tags(tag=tag)[0:40000]
        is_quantified_tags = self._features.is_quantified(tags = feature_tags)
        tags =  is_quantified_tags.loc[is_quantified_tags.loc[:,"quant_samples"].values > min_data_points,"tag"].values # self.get_feature_tags(tag=tag)['Q8TBN0','Q9HCD6']
        #get pairwise combinations 
        #combinations = list(itertools.permutations(tags,2))
        idx = np.stack(np.triu_indices(len(tags), k=1), axis=-1)
        combinations = tags[idx]
        query = (
            "UNWIND $combinations as combs "
            "MATCH (p1:Protein {tag : combs[0]})<-[rp1:QUANTIFIED]-(s:Sample)-[rp2:QUANTIFIED]->(p:Protein {tag : combs[1]}) "
            "WITH collect(rp2.value) as x, collect(rp1.value) as y, combs "
            "WITH apoc.coll.zip(x, y) AS pairs, apoc.coll.avg(x) AS meanX, apoc.coll.avg(y) AS meanY, x ,y, combs "
            "WHERE size(x) > $min_data_points AND size(y) > $min_data_points "
            "WITH "
            "   [p IN pairs | (p[0] - meanX) * (p[1] - meanY)] AS products, "
            "   [v IN x | (v - meanX)^2] AS xSquaredDiffs, "
            "   [v IN y | (v - meanY)^2] AS ySquaredDiffs, combs, size(pairs) as N "
            "WITH "
            "    apoc.coll.sum(products) / "
            "   (SQRT(apoc.coll.sum(xSquaredDiffs)) * SQRT(apoc.coll.sum(ySquaredDiffs))) AS pearson, combs, N "
            "MATCH (p1:Protein {tag : combs[0]}), ((p2:Protein {tag : combs[1]})) "
            "WHERE pearson > $r_thresh "
            "MERGE (p1)-[rp:CORRELATES_WITH]->(p2) "
            "SET rp.r = pearson, rp.created_at = timestamp(), rp.t =  pearson * SQRT(N-2) / SQRT(1-pearson^2), rp.N = N  "
            "RETURN count(rp) as count"
            )
        print(f"Starting to correlate all quantified features {len(tags)} of a proteome to each other. This is a very time consuming function and will take likely a couple of hours.")
        chunks = np.array_split(combinations, int(len(combinations)/chunk_size))   
        print(f"Data will be processing {len(combinations)} combinations in {len(chunks)} chunks (chunk_size: {chunk_size}).")    
        N = 0               
        for n,chunk in enumerate(chunks):
            r = self._driver.execute_query(query, combinations=chunk, result_transformer_=Result.value, r_thresh = cutoff, min_data_points = min_data_points)
            print("Chunk", n, r)
            N += r[0] #add number of created correlation relationshos 
        print(f"Correlation calculations done. {N} correlation relationships were added.")
    
    def delete(self, tag: str) -> bool:

        query = (
            "MATCH (prot:Proteome {tag : $proteome_tag}) "
            "SET prot.active = false, prot.modified_at = timestamp() "
            )
        try:
            self._driver.execute_query(query_=query,routing_="w")
            return True
        except Exception as e:
            print(e)
            return False 
        
    
    def exists(self, tag: str) -> bool:
        """Check if a proteome with the given tag exists.   
        Parameters
        ----------
        tag : str
            The proteome tag to check for existence.

        Returns
        -------
        bool
            True if the proteome exists, False otherwise.
        """
        
        query = (
            "MATCH (prot:Proteome {tag : $tag}) "
            "RETURN count(prot) > 0 as exists"
        )
        
        r = self._driver.execute_query(query=query, routing_="r", result_transformer_=Result.value, tag=tag)
        
        return r[0] if r else False
    
    def exist(self, tags : str|List[str]) -> bool:
        """Check if tag/tags exists. If list is given,
        then it checks if ALL exist. If one is missing, 
        False will be returned. 

        Parameters
        ----------
        tags : List[str]
            Proteome tags to check for existence.(Uniprot proteome ids)

        Returns
        -------
        bool
            If all given tags exists
        """
        
        if isinstance(tags,str):
            tags = [tags]
        
        query = ("MATCH (prot:Proteome) "
                 "WHERE prot.tag in $tags "
                 "RETURN prot.tag "
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
            "MATCH (a:Attribute {tag : 'att_proteome'})-[:HAS_TRAIT]->(av:Trait) "
            "RETURN properties(av) "
        )
        
        r = self._driver.execute_query(query,routing_="r",database_="neo4j", result_transformer_= Result.value)
        return [ri for ri in r]

    def get_features(self, tag: str) -> List[FeatureNeoModel]:
        
        query = (
            "MATCH (av:AttributeValue {tag : $tag}) "
            "MATCH (av)-[r:IN_PROTEOME]->(p:Protein) "
            "RETURN properties(p)"
        )
        
        r = self._driver.execute_query(query_=query,routing_="r",tag=tag)
        return [FeatureNeoModel(**d.data()) for d in r]
    

    def get_feature_tags(self, tag : str) -> List[str]:
        query = (
            "MATCH (av:AttributeValue {tag : $tag}) "
            "MATCH (av)<-[r:IN_PROTEOME]-(p:Protein) "
            "RETURN collect(p.tag) "
        )
        r = self._driver.execute_query(query_=query,routing_="r",tag=tag, result_transformer_=Result.value)
        return r[0]
    
    def get_feature_abundance_dist(self, tag : str) -> QuantileModel:
        """
        Get the abundance distribution of features for a specific proteome.
        """
        query = (
            "MATCH (prot:Proteome {tag : $tag}) "
            "MATCH (prot)<-[:IN_PROTEOME]-(p:Protein)<-[r:QUANTIFIED]-(s:Sample) "
            "RETURN apoc.agg.percentiles(r.value, [0,0.25,0.5,0.75,1.0]) as quantiles, count(r) as N "
        )
        
        r = self._driver.execute_query(query,routing_="r",result_transformer_=Result.data, tag = tag)
        if len(r) == 0: return None
        qs = r[0]["quantiles"]
        N = r[0]["N"]
        return QuantileModel(min = qs[0], q25 = qs[1], m = qs[2], q75 = qs[3], max = qs[4], N = N)

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
        self.insert_proteome_from_dataframe(data,proteome_tag,user_tag=user_tag)

    
    def insert_proteome_from_dataframe(self, data : pd.DataFrame, proteome_tag : str = "UP000005640", user_tag : str = None): 
        """Insert data from a Uniprot reference proteome to the database. 

        Parameters
        ----------
        data : pd.DataFrame
            The protein data with the following headers. The headers are required and the names match the Uniprot API:
            
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
    
        if any(column_name not in data.columns for column_name in ["Length","Gene Names","Entry","Sequence","Protein names","Gene Names (primary)","Sequence version"]):
            raise ValueError('Column names incomplete. Must have ["Length","Gene Names","Entry","Sequence","Protein names","Gene Names (primary)","Sequence version"]')
        
        query = (
            "MERGE (proteome:Proteome {tag : $proteome_attribute_tag}) "
            "ON CREATE "
            "SET proteome.created_at = timestamp(), proteome.user_tag = $user_tag "
            "ON MATCH "
            "SET proteome.modified_at = timestamp(), proteome.user_tag = $user_tag "
            "WITH proteome "
            "UNWIND $uniprot_features as row "
            "MERGE (protein:Protein {tag : row.Entry}) "
            "ON CREATE "
            "   SET protein += {aa_length : row.Length, gene_name : row.`Gene Names (primary)`, gene_names : row.`Gene Names`, protein_name : row.`Protein names`, created_at : timestamp(), proteome_tag : $proteome_tag, s : toLower(row.`Gene Names`)+' '+toLower(row.Entry)+' '+toLower(row.`Protein names`), viewed : 0} "
            "ON MATCH "
            "   SET protein.gene_names = row.`Gene Names`, protein.protein_name = row.`Protein names`, protein.gene_name = row.`Gene Names (primary)`, protein.aa_length = row.Length, protein.proteome_tag = $proteome_tag "
            "WITH protein, proteome, row "
            "MERGE (protein)-[r:IN_PROTEOME]->(proteome) "
            "MERGE (sequence:Sequence {content : row.Sequence, version : row.`Sequence version`}) "
            "MERGE (protein)-[:HAS_SEQUENCE]-(sequence) "
        )
        self._driver.execute_query(query, 
                                   proteome_attribute_tag = proteome_tag, 
                                   uniprot_features = data.to_dict(orient="records"), 
                                   proteome_tag = proteome_tag,
                                   user_tag = user_tag,
                                   routing_="w",
                                   database_="neo4j")
        

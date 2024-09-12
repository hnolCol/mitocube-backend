from typing import Optional,List

from neo4j import Driver, Result

from lib.data.database.abstract.Filter import FilterABC

from config.models.filter import FilterModel
from config.models.annotations.feature import FeatureModel

import pandas as pd 

class Neo4JFilter(FilterABC):
    
    def __init__(self, driver : Driver) -> None:
        ""
        self._driver = driver 
    
    def exists(self, tag : str) -> bool:
        ""
        ""
        query = (
            "WITH EXISTS {(f:Filter {tag : $tag})} as filter_exists "
            "RETURN filter_exists "
        )    
        r = self._driver.execute_query(query, tag = tag, result_transformer_=Result.value)
        return r[0]
    
    def add(self, 
                   protein_tags : List[str], 
                   proteome_tag : str, 
                   filter_tag : str, 
                   filter_text : str,
                   description : str,
                   publication : Optional[str] = None):
        """_summary_

        Parameters
        ----------
        protein_tags : List[str]
            _description_
        proteome_tag : str
            _description_
        filter_tag : str
            _description_
        filter_text : str
            The name that is visibile to the user on selection. 
        description : str
            The description that is displayed along the filter. 
        publication : str 
            A publication that (PUBMED ID) that can be used that describes the filter set. 
        """
        
        query = (
            "MERGE (f:Filter {tag : $tag}) "
            "ON CREATE "
            "SET f.created_at = timestamp(), f.proteome_tag = $proteome_tag, f.description = $description, f.text = $filter_text "
            "ON MATCH "
            "SET f.modified_at = timestamp(), f.proteome_tag = $proteome_tag, f.description = $description, f.text = $filter_text "
            "WITH f "
            )
        
        if publication is not None:
            
            query += (
                "MERGE (pub:Publication {tag : $publication}) "
                "ON CREATE "
                "SET pub.created_at = timestamp() "
                "WITH pub, f "
                "MERGE (f)-[:BASED_ON]->(pub) "
                "WITH f ")    
        
        query += (
            "MATCH (p:Protein) "
            "WHERE p.tag in $protein_tags "
            "MERGE (f)<-[r:PART_OF]-(p) "
            "WITH count(r) as count, f "
            "SET f.N = count "
            "RETURN count"
            
        )
        try:
            r = self._driver.execute_query(query, 
                                           protein_tags = protein_tags, 
                                           filter_text = filter_text,
                                           proteome_tag = proteome_tag, 
                                           tag = filter_tag, 
                                           description = description,
                                           publication = publication, 
                                           routing_="w", 
                                           database_="neo4j",
                                           result_transformer_=Result.value)
        except Exception as e : 
            return False, "An error was returned" + str(e)
        
        return True, f"Filter added. In total {r} proteins were found and added to the filter."
    
    def count_feaures(self, tag: str) -> int:
        
        query = (
            "MATCH (f:Filter {tag:$tag})-[:PART_OF]-(p:Protein) "
            "RETURN count(p)"
        )
        
        r = self._driver.execute_query(query_=query, routing_="r", result_transformer_=Result.value)
        return r [0]
    
    def get(self, tag : str = None, proteome_tags : List[str] = None, feature_tag : str = None) -> List[FilterModel]:
        ""
        if tag is not None:
            query = (
                "MATCH (f:Filter) "
                "WHERE f.tag = $tag "
                
            )
        elif proteome_tags is not None:
            query = (
                "MATCH (f:Filter) "
                "WHERE f.proteome_tag in $proteome_tags "
            )
        elif feature_tag is not None:
            query = (
                "MATCH (f:Filter)<-[:PART_OF]-(p:Protein) "
                "WHERE p.tag = $feature_tag "
            )
        else:
            query = (
                "MATCH (f:Filter) "
            )
        
        query += (
            "MATCH (f)-[:BASED_ON]-(pub:Publication) "
            "WITH {publication : pub.tag} as pub_tag, f "
            "RETURN apoc.map.merge(properties(f), pub_tag) "
        )
        r = self._driver.execute_query(query, 
                                    database_="neo4j", 
                                    routing_="r",
                                    feature_tag = feature_tag,
                                    tag = tag,
                                    proteome_tags = proteome_tags,
                                    result_transformer_= Result.value)
        return [FilterModel(**f) for f in r] 
        
        
    def get_features(self, tag : str) -> List[FeatureModel]:
        """Returns the proteins associated with the filter. 
        Since filters are proteome_id specific, the returned list of
        features is also of a specific proteome_id. 

        Parameters
        ----------
        tag : str
            Filter tag. 

        Returns
        -------
        List[FeatureNeoModel]
            The proteins that are part of the filter
        """
        query = ("MATCH (f:Filter {tag : $tag}) "
                 "MATCH (f)<-[:PART_OF]-(p:Protein) "
                 "RETURN properties(p) "
                 )
        
        try:
            r = self._driver.execute_query(query , 
                                        database_="neo4j", 
                                        routing_="r", 
                                        result_transformer_= Result.value,
                                        tag = tag)
        except Exception as e:
            print(e)
            print("There has been an error. ")
            return [] 
        
        return [FeatureModel(**f) for f in r]
    
    
    def get_feature_quant(self, tag : str, ascending : bool = True, limit : int = None, include_not_quantified : bool = True) -> pd.DataFrame:
        """Calculates the number of quantifications in a submission dataset for the given tag. 
        Note that this does not count the number of samples/files that quantified the protein but just 
        the submission, hence if a single run identified/quantified the feature tag, it will be counted equally. 

        Parameters
        ----------
        tag : str
            The filter tag
        ascending : bool, optional
            If the result should be sorted in ascending order, by default True
        limit : int, optional
            The maximum number of entries to be returned, by default None
        include_not_quantified : bool, optional
            If also proteins should be included that have never been identified/quantified, by default True

        Returns
        -------
        pd.DataFrame
            pandas data frame with the following columns:
                - tag (str) : feature tag 
                - n (int) : number of submissions that quantified the feature tag 
                - submission (List[str]) : The list of submissions that quantified it. If not a single submission 
                quantified the protein, the list is empty. 
        """
            
        if include_not_quantified:
            
            query =  (
                "MATCH (f:Filter {tag : $tag})<-[:PART_OF]-(p:Protein) "
                "CALL {"
                "WITH p "
                "MATCH (p)-[r:QUANTIFIED_IN]->(submission:Submission) "
                "RETURN p.tag as tag, count(r) as n, [submission IN collect(DISTINCT submission) | submission.tag] as submission_tags ORDER BY n " 
                "UNION "
                "WITH p "
                "MATCH (p)"
                "WHERE NOT EXISTS{(p)-[:QUANTIFIED_IN]-(:Submission)} "
                "RETURN p.tag as tag, 0 as n, [] as submission_tags " 
                "} "
                "RETURN tag, n, submission_tags "
            )
        else:
            query = (
                "MATCH (f:Filter {tag : $tag})<-[:PART_OF]-(p:Protein)-[r:QUANTIFIED_IN]->(submission:Submission) "
                "RETURN p.tag as tag, count(r) as n, [submission IN collect(DISTINCT submission) | submission.tag] as submission_tags ORDER BY n " 
            )
            
        if ascending:
            query += "ORDER BY n ASC " 
        else:
            query += "ORDER BY n DESC " 
        if limit is not None:
            query += "LIMIT $limit"
            
        
        r = self._driver.execute_query(query, routing_="r",result_transformer_=Result.to_df, tag = tag, limit=limit)
        return r 
    
    def get_overlap_with_dataset_quant(self, tags : List[str], submission_tags : List[str]) -> pd.DataFrame:
        """Get the number of features that are in the filter 
        and were quantified by a set of submissions. 

        Parameters
        ----------
        tag : List[str]
            The filter tag
        submission_tags : List[str]
            _description_

        Returns
        -------
        pd.DataFrame
            - index (str): Filter tags
            - submission_tag(str): The submission tag
            - N(int) - The number of features quantified 
            - total(int) - The total number of features in the filter set.
        """
        
        query = ("MATCH (submission:Submission) "
                 "WHERE submission.tag in $submission_tags "
                 "MATCH (f:Filter)<-[:PART_OF]-(p:Protein)-[:QUANTIFIED_IN]-(submission) "
                 "WHERE f.tag in $tags "
                 "WITH count(p) as N, submission.tag as submission_tag, f.N as total, f.tag as tag "
                 "RETURN tag, submission_tag, N, total "
                 )

        r = self._driver.execute_query(query, 
                                       routing_="r", 
                                       result_transformer_=Result.to_df, 
                                       tags = tags, 
                                       submission_tags = submission_tags)
        return r.set_index("tag")
    
    def get_abundance_distribution(self, tag : str, quantiles : List[float] = [0.25,0.5,0.75]) -> List[float]:
        """Returns the abundances of proteins of a particular filter for the 
        given quantiles. 

        Parameters
        ----------
        tag : str
            The filter tag
        quantiles : List[float], optional
            The quantiles to get and return, by default [0.25,0.5,0.75]

        Returns
        -------
        List[float]
            The length of the list equals the list of the argument 'quantiles'. 
            If the filter_tag is not present in the database, returns a list
            of [None] * len(quantiles). 
        """
        query = (
            "MATCH (f:Filter {tag:$tag})<-[:PART_OF]-(p:Protein)-[r:QUANTIFIED_IN]->(submission:Submission) "
            "RETURN apoc.agg.percentiles(r.avg_log2_abundance, $quantiles) as quantiles"
        )
        
        r = self._driver.execute_query(query,routing_="r",quantiles = quantiles, tag = tag, result_transformer_=Result.value)
        return r[0]
        
    def isin(self, tag: str, feature_tags: List[str]) -> pd.Series:
        query = (
            "MATCH (p:Protein) "
            "WHERE p.tag in $feature_tags "
            "RETURN p.tag as tag, EXISTS {(f:Filter {tag : $tag})<-[:PART_OF]-(p)} as isin"
        )

        r = self._driver.execute_query(query,routing_="r",result_transformer_=Result.to_df, feature_tags=feature_tags,tag=tag)
        r = r.set_index(keys="tag")
        return r["isin"]
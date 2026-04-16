
from typing import Tuple, List, Dict, Literal
from collections import OrderedDict
from neo4j import Driver, Result
import numpy as np 
import pandas as pd 
from scipy.stats import f_oneway
from lib.database.abstract.Meta import MetaABC
from lib.database.abstract.Dataset import DatasetABC

from lib.database.Neo4JDatabase import Neo4JFactory




def transform_query_result(result):
    "Transforms the result into a list of data."
    return result.data()[0]["query_result"]

class Neo4JDataset(DatasetABC):
    
    def __init__(self, driver : Driver, meta : MetaABC) -> None:
        
        self._driver = driver
        self.meta = meta 
        self.factory = Neo4JFactory(driver)
    
    def exists(self, tag : str) -> bool:
        "Checks if the submission has data (e.g. quantified proteins). This is not meant to check if a submission exists."
        query = (
            "WITH EXISTS {(submission:Submission {tag : $tag})-[:HAS_SAMPLE]->(s:Sample)-[:QUANTIFIED]->(pg:ProteinGroup)} as submission_has_quant_data "
            "RETURN submission_has_quant_data "
        )    
        r = self._driver.execute_query(query, tag = tag, result_transformer_=Result.value)
        return r[0]
    
    def _get_variance_in_groups(self, tag : str, data_table : pd.DataFrame)-> pd.Series:
        "Calculate the onway ANOVA F-value when splitting the data in the individual groups" 
       # total_variance = data_table.var(axis=1)
        _, sample_attributes_map = self.meta.get_sample_attributes_and_genotypes(tag)
        attribute_tags = [attr_tag for attr_tag in sample_attributes_map.columns.values if attr_tag != "sample_text"] #sample text is always returned. 
        grouped_sample_attributes = sample_attributes_map.groupby(by=attribute_tags)
        data_for_test = [data_table.iloc[:,group_data.index].values for group, group_data in grouped_sample_attributes]
        #returns F-value and p-values
        F,p = f_oneway(*data_for_test,axis=1,)
        F = pd.Series(F,index=data_table.index)
        return F
    
        
    def insert(self, data_table : pd.DataFrame, tag : str):
        ""
        #F = self._get_variance_in_groups(tag, data_table)
        
        # with self._driver.session() as session:
        #     session.execute_write(self._add_dt, data_table, tag, F)
            
            
        #set sample index 
        data_table.columns = np.arange(data_table.columns.size)
        #print(data_table.reset_index(names="p_tag").melt(id_vars="p_tag", var_name="sample_index"))
        X = data_table.reset_index(names="p_tag").melt(id_vars="p_tag", var_name="sample_index").dropna(subset=["value"])
       # print(X)
        print(X.index.size)
        
        for sample_index, sample_data in X.groupby("sample_index"):
            print(sample_data.index)
            query = (
                "MATCH (submission:Submission {tag : $tag}) "
                "MATCH (sample:Sample {index : $sample_index}) "
                "UNWIND $quant_values as q_value "
                "MATCH (p:Protein {tag : q_value.p_tag}) "
                "MERGE (p)<-[r:QUANTIFIED]-(sample) "
                "SET r.value = q_value.value "
                "RETURN count(r) "
            )
            r = self._driver.execute_query(query, tag = tag, 
                                           sample_index = sample_index,
                                           quant_values = sample_data[["p_tag","value"]].to_dict(orient="records"))
            
            
            
    @staticmethod
    def _add_dt(tx, data_table: pd.DataFrame, tag  : str, F : pd.Series):
        
        
        data_table = data_table.dropna(how="all")
        data_table.columns = np.arange(data_table.columns.size) #TODO Change here to match the exact index (From meta?) 
        is_nan = np.isnan(data_table).values
        tags = data_table.index.values 
        values = data_table.values
        mean_values = data_table.mean(axis=1)
        
        
        props = [{"tag" : tag, 
                  "mean_q" : mean_values.loc[tag],
                  "f" : F.loc[tag],
                  "qs" : [v for m,v in enumerate(values [n,:]) if not is_nan[n,m]],
                  "sample_index" : [data_table.columns[idx] for idx in range(data_table.columns.size) if not is_nan[n,idx]]
                  } for n,tag in enumerate(tags)]
        
        query = (
            "MATCH (submission:Submission {tag : $tag}) "
            "UNWIND $props as prop "
            "MATCH (p:Protein {tag: prop.tag}) "
            "MERGE (p)-[r:QUANTIFIED_IN]->(submission) "
            "SET r += {F : prop.f, qs : prop.qs, sample_index : prop.sample_index, created_at : timestamp(), avg_log2_abundance : prop.mean_q} " #variance : prop.var, max_variance_attribute : prop.var_attr
            #"SET r.points = [p IN prop.points | point({x: p.x, y : p.y})] "
            "RETURN count(r) as count " 
        )
        
        r = tx.run(query, props = props, tag = tag)
        
        
        print("dataset added.")
    
    # def add_datatable3(self, data_table : pd.DataFrame, main_chunk_size = 2000):
    #     ""
    #     data_table_melt = data_table.reset_index().melt(id_vars="Key").dropna(subset=["value"])
    #     #data_table_chunks = np.array_split(data_table_melt, data_table_melt.index.size / main_chunk_size)
    #     print("adding datatable with sample relations")
       
    #     with self._driver.session() as session:
    #         session.execute_write(self._add_q_values, data_table = data_table_melt)
       
    # @staticmethod
    # def _add_q_values(tx, data_table : pd.DataFrame, chunk_size : int = 10000, relation_label : str = "QUANTIFIED"):
    #     ""
    #     chunks = np.array_split(data_table, data_table.index.size / chunk_size)
    #     for c in chunks:
    #         if c.index.size == 0: continue
    #         query = (
    #             f"UNWIND $props AS prop "
    #             "MATCH (s:Sample {tag : prop.variable}) "
    #             "MATCH (p:Protein {tag: prop.Key}) " #this should be match instead of merge! -> if dataset created before.
    #             "WITH s, p, prop "
    #             f"MERGE (s)-[r:{relation_label}]->(p) "
    #             "SET r.value = prop.value, r.tag =  "
    #             "RETURN s, p"
    #         )
    #         r = tx.run(query, props = c.to_dict(orient="records"))
    
    
    def get_abundance_distribution(self, tags : List[str] = None, filter_tag : str = None, quantiles : List[float] = [0.25,0.5,0.75]) -> pd.DataFrame:
        ""
        if tags is None and filter_tag is None:
            query = (
                "MATCH (submission:Submission)-[r:QUANTIFIED_IN]-(p:Protein) "
            )
        elif tags is None and filter_tag is not None:
            ##filter tag exists 
            query = (
                "MATCH (submission:Submission)-[r:QUANTIFIED_IN]-(p:Protein)-[:PART_OF]->(f:Filter) "
                "WHERE f.tag = $filter_tag "
            )
        elif tags is not None and filter_tag is None:
            query = (
                "MATCH (submission:Submission)-[r:QUANTIFIED_IN]-(p:Protein) "
                "WHERE submission.tag in $tags "
            )
        elif filter_tag is not None and tags is None:
            query = (
                "MATCH (submission:Submission)-[r:QUANTIFIED_IN]-(p:Protein)-[:PART_OF]->(f:Filter) "
                "WHERE f.tag = $filter_tag "
            )
        query += "RETURN apoc.agg.percentiles(r.avg_log2_abundance, $quantiles) as quantiles"
        r,_,_ = self._driver.execute_query(query, 
                                           tags=tags, 
                                           filter_tag = filter_tag, 
                                           quantiles = quantiles, 
                                           result_transformer_=Result.df)
        print(r,"ABUNDANCE")
        return r 
        
    
    def get_dataset_node(self, tag: str) -> Dict:
        "Returns the dataset node properties by the tag." 
        query = (
            "MATCH (d:Dataset {tag : $tag}) "
            "RETURN properties(d) as query_result"
        )

        r = self._driver.execute_query(query, tag = tag, 
                                    result_transformer_=transform_query_result, 
                                    database_="neo4j", 
                                    routing_="r")
        return r
        
        
    
    
    
    def get_precursor_datatable(self, tag : str, sample_tags : List[str] = None, annotation_tag : str = None, use_sample_tags : bool = False) -> pd.DataFrame:
        #TODO refine this... 
        if annotation_tag is None:
            query = (
            "MATCH (submission:Submission {tag : $tag})-[:HAS_SAMPLE]->(sample:Sample)-[r:QUANTIFIED]->(p:Peptide) "
                )
        else:
            query = (
                "MATCH (a:Annotation) "
                "WHERE a.tag = $annotation_tag "
                "MATCH (submission:Submission {tag : $tag})-[:HAS_SAMPLE]->(sample:Sample)-[r:QUANTIFIED]->(p:Peptide) "
                "WHERE EXISTS {(a)-[:ANNOTATES]->(p)} "
            )
            
            
        if sample_tags is not None and len(sample_tags) > 0:
            if annotation_tag is None:
                query += "WHERE sample.tag IN $sample_tags " 
            else:   
                query += "AND sample.tag IN $sample_tags "
            
        
        query += "RETURN p.tag as tag, collect(r.value) as qs, collect(sample.sample_index) as idx, collect(sample.tag) as sample_tags "
        r = self._driver.execute_query(query, routing_="r", tag = tag, result_transformer_=Result.to_df, sample_tags = sample_tags, annotation_tag = annotation_tag)
        
        if use_sample_tags:
            datatable = r.explode(["qs","sample_tags"]).pivot(index="tag",columns="sample_tags",values="qs").astype(float)
        else:
            datatable = r.explode(["qs","idx"]).pivot(index="tag",columns="idx",values="qs").astype(float)
        return datatable
    
        
    
    
    def get_datatable(self, tag : str, sample_tags : List[str] = None, annotation_tag : str = None, use_sample_tags : bool = False, level : Literal["protein","precursor"] = "protein") -> pd.DataFrame:
        "Returns a table sample indexes as columns and protein tags as index."

        
        if annotation_tag is None:
            query = (
            "MATCH (submission:Submission {tag : $tag})-[:HAS_SAMPLE]->(sample:Sample)-[r:QUANTIFIED]->(pg:ProteinGroup) "
                )
        else:
            query = (
                "MATCH (submission:Submission {tag : $tag})-[:HAS_SAMPLE]->(sample:Sample)-[r:QUANTIFIED]->(pg:ProteinGroup)-[:HAS_PROTEINS]->(p:Protein)<-[:ANNOTATES]-(a:Annotation {tag : $annotation_tag}) "
            )
            
        if sample_tags is not None and len(sample_tags) > 0:
                query += "WHERE sample.tag IN $sample_tags " 
        
        query += "RETURN pg.tag as tag, collect(r.value) as qs, collect(sample.sample_index) as idx, collect(sample.tag) as sample_tags "
       
        r = self._driver.execute_query(query, routing_="r", tag = tag, result_transformer_=Result.to_df, sample_tags = sample_tags, annotation_tag = annotation_tag)
       # r = r.drop_duplicates(subset=["tag","sample_tags"])
        if use_sample_tags:
            datatable = r.explode(["qs","sample_tags"], ignore_index=True).drop_duplicates(subset=["tag","sample_tags"]).pivot(index="tag",columns="sample_tags",values="qs").astype(float)
        else:
            datatable = r.explode(["qs","idx"], ignore_index=True).drop_duplicates(subset=["tag","idx"]).pivot(index="tag",columns="idx",values="qs").astype(float)
        return datatable
        
        
    def is_quantified(self, tag : str, protein_tags : List[str]) -> pd.Series:
        ""
        query = (
            "MATCH (submission:Submission {tag : $tag}) "
            "UNWIND $protein_tags AS protein_tag "
            "MATCH (p:Protein {tag : protein_tag}) "
            "RETURN protein_tag as tag, EXISTS {(submission)-[:HAS_SAMPLE]->(s:Sample)-[:QUANTIFIED]->(p)} as quantified "
        )
        
        r = self._driver.execute_query( 
                                        query, tag = tag, 
                                        protein_tags = protein_tags,
                                        result_transformer_= Result.to_df, 
                                        database_="neo4j", 
                                        routing_="r")
        
        r = r.reset_index("tag")
        return r["quantified"]
        
      
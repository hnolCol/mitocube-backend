from typing import List, Dict
from neo4j import Driver, Result

from lib.database.abstract.Samples import SamplesABC
from services.encryption import create_hierarchical_hash
from config.models.submissions.submissions import AttributeTree
from config.models.conditions_applications import ConditionApplicationAttributeModel
from lib.database.abstract.ConditionApplications import ConditionApplicationABC
from config.models.samples import SampleModel
import pandas as pd
import uuid
class Neo4JSamples(SamplesABC):
    """
    Neo4J implementation of the SamplesABC interface.
    """
    def __init__(self, driver : Driver, condition_applications : ConditionApplicationABC):
        self._driver = driver
        self._condition_applications = condition_applications

    def _get_sample_tag(self, sample_name : str, submission_tag : str) -> str:
        """Generates a sample tag based on the sample name and submission tag.
        
        Parameters
        ----------
        sample_name : str
            The name of the sample.
        submission_tag : str
            The tag of the submission to which the sample belongs.
        
        Returns
        -------
        str
            A unique sample tag.
        """
        return f"{submission_tag}|{sample_name}"

    def count(self, 
              has_protein_quantification : bool = False, 
              has_peptide_quantification : bool = False,
              protein_group_tag : str = None, 
              submission_tag : str = None, 
              trait_tag : str = None,
              instrument_tag : str =None,
              genotype_tag : str = None) -> int:

        "Counts the number of samples. If a specific trait tag is provided, the number of samples with a trait will be counted."
        if protein_group_tag is not None:
            query = (
                "MATCH (s:Sample)-[:QUANTIFIED]->(pg:ProteinGroup {tag : $protein_group_tag})-[:HAS_PROTEINS]->(p:Protein)-[:IN_PROTEOME]-(proteome:Proteome) "
            )
        elif trait_tag is not None:
            query = (
                "MATCH (s:Sample)<-[:HAS_SAMPLE]-(submission:Submission)-[:HAS_]->(trait:Trait) " ## TO DO: This is not correct, need to traverse the condition application tree
                "WHERE trait.tag = $trait_tag "
            )
        elif submission_tag is not None:
            query = (
                "MATCH (s:Sample)<-[:HAS_SAMPLE]-(submission:Submission {tag : $submission_tag}) "
            )
        elif genotype_tag is not None:
            query = (
                "MATCH (s:Sample)-[:HAS_GENOTYPE]->(g:Genotype {tag : $genotype_tag})"
            )
        elif instrument_tag is not None:
            query = (
                "MATCH (s:Sample)<-[:MEASURED]-(t:Trait {tag : $instrument_tag}) "
            )
        else:
            query = (
                "MATCH (s:Sample) "
            )
        
        ## handle quantification filters
        if trait_tag is not None:
            query += (
                "AND "
            )
        elif (has_protein_quantification or has_peptide_quantification):
            query += (
                "WHERE "
            )

        if has_protein_quantification:
            if protein_group_tag is not None: 
                query += (
                " EXISTS {(s)-[:QUANTIFIED]->(pg:ProteinGroup)-[:HAS_PROTEINS]->(:Protein)-[:IN_PROTEOME]-(proteome)} "
            )
            else:
                query += (
                " EXISTS {(s)-[:QUANTIFIED]->(:ProteinGroup)} "
            )
        if has_peptide_quantification:
            if has_protein_quantification:
                query += "AND "
            query += (
                "EXISTS {(s)-[:QUANTIFIED]->(:Peptide)} "
            )
        query += (
            "RETURN count(s) as count "
        )
        
        print(query)
            
        
        r = self._driver.execute_query(query, routing_="r", result_transformer_=Result.data, genotype_tag = genotype_tag, trait_tag = trait_tag, submission_tag = submission_tag, protein_group_tag = protein_group_tag)
        return r[0]["count"] if len(r) > 0 and "count" in r[0] else 0



    def exists(self, tag : str) -> bool:
        "Check if a sample is associated with the given tag."
        
        query = (
            "WITH EXISTS {(s:Sample {tag : $tag})} as exists "
            "RETURN exists"
        )
        
        r = self._driver.execute_query(query,routing_="r",result_transformer_=Result.value, tag = tag)
        return r[0]


    def get(self, tag : str) -> SampleModel:
        "Returns the sample information for a given sample tag."
        
        query = (
            "MATCH (s:Sample {tag : $tag}) " 
            "RETURN {tag : s.tag, text : s.name, index : s.sample_index, created_at : s.created_at}  "
        )
        
        r = self._driver.execute_query(query,routing_="r",result_transformer_=Result.value, tag = tag)

        return  r[0] if len(r) > 0 else None


    def get_quantified_data_for_feature(self, tag : str, feature_tag : str) -> float: 
        """Get the quantified data for a given sample and feature.
        A feature may be protein group or peptide.
        """
        
        if self.exists(tag = tag) is False: raise ValueError("Sample tag does not exist. ")
        
        query = (
            "MATCH (s:Sample {tag : $tag})-[r:QUANTIFIED]->(f:ProteinGroup|Peptide {tag : $feature_tag}) "
            "RETURN r.value as value "
        )
        
        r = self._driver.execute_query(query,routing_="r",result_transformer_=Result.value, tag = tag, feature_tag = feature_tag)
        return r[0] if len(r) > 0 else None
    
        
    def insert(self, submission_tag : str, sample_name : str, sample_index : int) -> str:
        "Insert a new sample to a given submission" 
        #if self.exists(tag = tag): raise ValueError("Sample tag exists already. ")
        sample_tag = self._get_sample_tag(sample_name, submission_tag)
        if self.exists(tag = sample_tag): raise ValueError("Sample tag exists already. ")
        query = (
            "MATCH (s:Submission {tag : $submission_tag}) "
            "MERGE (sample:Sample {tag : $sample_tag, text : $sample_name, sample_index : $sample_index, created_at : timestamp()}) "
            "MERGE (s)-[:HAS_SAMPLE]->(sample) "
            "RETURN sample.tag "
        )

        r = self._driver.execute_query(query, routing_="w", result_transformer_=Result.value, sample_tag=sample_tag,
                                   submission_tag=submission_tag, sample_name=sample_name, sample_index=sample_index)
        return r[0] if len(r) > 0 else None
     
    
    def insert_condition_application(self, sample_tag : str, sample_data : List[AttributeTree]):
        """Insert a condition application for a given sample.
        The condition application is a hierarchical structure that describes the conditions applied to the sample. 
        The data structure is used to generate a unique tag for the condition application. Hence, if the datastructure is the same, the same tag will be used connecting the 
        samples to the same condition node. 

        Parameters
        ----------
        sample_tag : str
            The tag of the sample.
        sample_data : List[AttributeTree]
            The condition data to insert.
        This data should be a list of AttributeTree objects, where each object represents a condition application.
        Each dictionary should have the following structure, here is a complex example having multiple attributes and traits:
        {
            "type": "attribute",
            "tag": "att_compound",
            "children": [               
                {
                    "type": "trait",
                    "tag": "att_compound:dmso",
                    "children": [       
                        {
                            "type": "attribute",
                            "tag": "att_concentration",
                            "children": [
                                {"type": "trait", "tag": "mM", "value": 2, 
                                 "children": [
                                     {"type" : "attribute", "tag" : "temperature", "children" : [
                                         {"type" : "trait", "tag" : "high"}
                                     ]}
                                 ]}
                            ]
                        },
                        {
                            "type": "attribute",
                            "tag": "Time",
                            "children": [
                                {"type": "trait", "tag": "h", "value": 5, "children": []}
                            ]
                        }
                    ]

        """
        ts = []
        for attribute_tree in sample_data:
            tag = self._condition_applications.insert(condition_application=attribute_tree)
            ts.append(tag)

        ##connect sample to condition applications
        query = ("MATCH (s:Sample {tag : $sample_tag}) "
                 "MATCH (ca:ConditionApplication) "
                 "WHERE ca.tag IN $tags "
                 "MERGE (s)-[r:HAS_APPLICATION]->(ca) "
                 "SET r.created_at = timestamp() ")
        
        self._driver.execute_query(query, routing_="w", sample_tag=sample_tag, tags=ts)
        
        
        
    def get_condition_applications(self, tag: str, group_by_attribute : bool = False) -> List[str]|List[ConditionApplicationAttributeModel]:
        """Get all condition procedures for a given sample. If no sample tag is provided, all condition procedures are returned.
        You may also sort the results by the most frequent condition procedures.
        If only one tag is found, a single string is returned. If no tag is found, an empty list is returned. 
        
        Parameters
        ----------
        tag : str
            The tag of the sample to get the condition procedures for.
        group_by_attribute : bool, optional
            If True, the results are grouped by attribute and returned as a list of ConditionApplicationAttribute
            
        Returns
        -------
        List[str]|str
            A list of condition procedure tags. If only a single tag is found, a single string is returned.
            If no tag is found, an empty list is returned.
        """
            
        query =  "MATCH (sample:Sample {tag : $tag})-[:HAS_APPLICATION]->(condition:ConditionApplication)" 
        if group_by_attribute:
            query += "MATCH (condition)-[:OF_ATTRIBUTE]->(a:Attribute) RETURN a.tag, collect(condition.tag) "
        else:
            query += "RETURN collect(condition.tag) "
        r = self._driver.execute_query(query, routing_="r", tag = tag, result_transformer_=Result.values if group_by_attribute else Result.value)
        if group_by_attribute:
            return [ConditionApplicationAttributeModel(attribute_tag = ri[0], condition_application_tags = ri[1]) for ri in r]
        return r[0] if len(r) > 0 else []
        
    
    def get_samples_by_genotype(self, genotype_tag : str):
        "" 
        query = (
            "MATCH (s:Sample)-[:HAS_GENOTYPE]->(g:Genotype) "
            "WHERE g.tag = $genotype_tag "
            "RETURN s.tag as tag, g.tag as genotype_tag "
        )
        
        r = self._driver.execute_query(query, routing_="r", result_transformer_=Result.data, genotype_tag=genotype_tag)
        return r 

    def get_sample(self, tag : str) -> Dict:
        "Returns a sample an its trait as well genotype annotation."
        
        query = (
            "MATCH (s:Sample {tag : $tag}) " 
            "RETURN {tag : s.tag, text : s.text, sample_index : s.sample_index, created_at : s.created_at}  "
        )
        
        r = self._driver.execute_query(query,routing_="r",result_transformer_=Result.data, tag = tag)
        print(r)
        return  r[0] if len(r) > 0 else None


    def get_sample_tag_by_index_and_submission(self, sample_index : int, submission_tag : str) -> List[str]:
        "Returns a sample an its trait as well genotype annotation."
        
        query = (
            "MATCH (s:Sample {sample_index : $sample_index})<-[:HAS_SAMPLE]-(submission:Submission {tag : $submission_tag}) " 
            "RETURN s.tag ORDER BY s.sample_index ASC "
        )
        
        r = self._driver.execute_query(query,routing_="r",result_transformer_=Result.value, sample_index = sample_index, submission_tag = submission_tag)
        print(r)
        return  r[0] if len(r) > 0 else None

    def get_condition_applications_by_sample_index_for_submission(self, submission_tag : str, join : str = ";", pivot : bool = True) -> pd.DataFrame:
        """Get all condition procedures for all samples in a submission, indexed by sample index. 
        
        Parameters
        ----------
        submission_tag : str
            The submission tag to get the condition procedures for.
        join : str, optional
            If provided, multiple condition procedure tags will be joined into a single string using this separator.
        pivot : bool, optional
            If True, the result will be pivoted to have attributes as columns.
        Returns
        -------
        pd.DataFrame
            A DataFrame with sample indices as index and condition procedures as columns.
            The columns names represent the instance attribute (e.g. att_environment).
            The values are the condition procedure tags. 
            Multiple tags are separated by a semicolon, if join is provided.
            
        """
        
        query = (
            "MATCH (submission:Submission {tag : $submission_tag})-[:HAS_SAMPLE]->(s:Sample)-[:HAS_APPLICATION]->(ca:ConditionApplication)-[:OF_ATTRIBUTE]->(a:Attribute) "
            "RETURN s.sample_index as sample_index, a.tag as attribute_tag, collect(ca.tag) as condition_tags "
            "ORDER BY s.sample_index ASC "
        )
        df = self._driver.execute_query(query, routing_="r", result_transformer_=Result.to_df, submission_tag=submission_tag)
        df.set_index("sample_index", inplace=True)
        if join is not None:
            df["condition_tags"] = df["condition_tags"].apply(lambda x: ";".join(x))
            if pivot:
                df = df.pivot_table(index=df.index, columns="attribute_tag", values="condition_tags", aggfunc='first')
        return df

    
        # add useGetSampleGenotype
    
    
    
    def get_sample_genotype(self, tag : str) -> str :
        """Get the genotype tag associated with a given sample.

        Parameters
        ----------
        tag : str
            The sample tag whose genotype should be returned.

        Returns
        -------
        str
            The genotype tag linked to the given sample.
        """

        query = (
            "MATCH (s:Sample)-[:HAS_GENOTYPE]->(g:Genotype)"
            "RETURN g.tag"
        )


        genotype = self._driver.execute_query(query, tag=tag, routing_="r")
        return genotype
from typing import List, Dict, Literal
from neo4j import Driver, Result
from datetime import datetime

from lib.database.abstract.Samples import SamplesABC
from config.models.submissions.submissions import AttributeTree
from config.models.conditions_applications import ConditionApplicationAttributeModel
from lib.database.abstract.Genotypes import  GenotypeABC
from lib.database.abstract.Annotations import AnnotationsABC
from lib.database.abstract.ConditionApplications import ConditionApplicationABC
from config.models.samples import SampleModel, SampleUpdateModel
import pandas as pd

import re

from config.models.calculations.quantile import QuantileModel
class Neo4JSamples(SamplesABC):
    """
    Neo4J implementation of the SamplesABC interface.
    """
    def __init__(self, driver : Driver, condition_applications : ConditionApplicationABC, genotypes : GenotypeABC, annotations : AnnotationsABC):
        self._driver = driver
        self._condition_applications = condition_applications
        self._genotypes = genotypes
        self._annotations = annotations
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
              genotype_tag : str = None,
              ) -> int:

        "Counts the number of samples. If a specific trait tag is provided, the number of samples with a trait will be counted."
        if protein_group_tag is not None:
            query = (
                "MATCH (s:Sample)-[:QUANTIFIED]->(pg:ProteinGroup {tag : $protein_group_tag}) "
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
                " EXISTS {(s)-[:QUANTIFIED]->(pg:ProteinGroup)} "
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
                    
        r = self._driver.execute_query(query, routing_="r", result_transformer_=Result.data, genotype_tag = genotype_tag, trait_tag = trait_tag, submission_tag = submission_tag, protein_group_tag = protein_group_tag, instrument_tag = instrument_tag)
        return r[0]["count"] if len(r) > 0 and "count" in r[0] else 0


    def count_quantified_protein_groups(self, tag : str, submission_tag : str) -> int:
        """Counts the number of quantified protein groups for a given sample.

        Parameters
        ----------
        submission_tag : str
            The tag of the submission.

        Returns
        -------
        List[Dict]
            A list of dictionaries, each containing the sample tag and the count of quantified protein groups.
        """
        
        query = (
            "MATCH (submission:Submission {tag : $submission_tag})-[:HAS_SAMPLE]->(s:Sample {tag : $tag}) "
            "MATCH (s)-[:QUANTIFIED]->(pg:ProteinGroup) "
            "RETURN count(DISTINCT pg) as count "
        )
        
        r = self._driver.execute_query(query, routing_="r", tag = tag, result_transformer_=Result.data, submission_tag=submission_tag)
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
            "RETURN {tag : s.tag, text : s.name, index : s.sample_index, created_at : s.created_at, excluded : coalesce(s.excluded, false)}  "
        )
        
        r = self._driver.execute_query(query,routing_="r",result_transformer_=Result.value, tag = tag)

        return  r[0] if len(r) > 0 else None


    def get_quantified_data_for_feature(self, tag : str, feature_tag : str, metrics : Literal["raw","z_score_sample","z_score_protein_group","log2_fc_vs_mean"] = "raw") -> float: 
        """Get the quantified data for a given sample and feature.
        A feature may be protein group or peptide.
        """
        
        metrics_mapping = {
            "raw" : "value",
            "z_score_sample" : "z_score_sample",
            "z_score_protein_group" : "z_score_protein_group",
            "log2_fc_vs_mean" : "log2_fc_vs_mean"
        }
        
        if metrics not in metrics_mapping:
            raise ValueError(f"Invalid metrics value. Allowed values are: {list(metrics_mapping.keys())}")
        
        if self.exists(tag = tag) is False: raise ValueError("Sample tag does not exist. ")
        
        query = (
            "MATCH (s:Sample {tag : $tag})-[r:QUANTIFIED]->(f:ProteinGroup|Peptide {tag : $feature_tag}) "
            f"RETURN r.{metrics_mapping[metrics]} as value "
        )
        
        r = self._driver.execute_query(query,routing_="r",result_transformer_=Result.value, tag = tag, feature_tag = feature_tag)
        return r[0] if len(r) > 0 else None
    
        

    def insert(self, submission_tag : str, sample_name : str, sample_index : int, replicate: int = None, return_tag_if_exists : bool = False, connect_if_exists : bool = False) -> str:
        "Insert a new sample to a given submission" 
        #if self.exists(tag = tag): raise ValueError("Sample tag exists already. ")
        sample_tag = self._get_sample_tag(sample_name, submission_tag)
        if self.exists(tag = sample_tag):
            if return_tag_if_exists:
                if connect_if_exists:
                    query = (
                        "MATCH (s:Submission {tag : $submission_tag}) "
                        "MATCH (sample:Sample {tag : $sample_tag}) "
                        "MERGE (s)-[:HAS_SAMPLE]->(sample) "
                        "RETURN sample.tag "
                    )
                    r = self._driver.execute_query(query, routing_="w", result_transformer_=Result.value, sample_tag=sample_tag, submission_tag=submission_tag)
                return sample_tag
            else:
                raise ValueError("Sample tag exists already. ")
        query = (
            "MATCH (s:Submission {tag : $submission_tag}) "
            "MERGE (sample:Sample {tag : $sample_tag, text : $sample_name, sample_index : $sample_index, created_at : timestamp()}) "
            "ON CREATE SET sample.replicate = $replicate "
            "MERGE (s)-[:HAS_SAMPLE]->(sample) "
            "RETURN sample.tag "
        )

        r = self._driver.execute_query(query, routing_="w", result_transformer_=Result.value, sample_tag=sample_tag,
                                   submission_tag=submission_tag, sample_name=sample_name, sample_index=sample_index, replicate=replicate)
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
            for c in attribute_tree.children:
                #separate on first level children
                updated_tree = AttributeTree(tag = attribute_tree.tag, type = attribute_tree.type, value = attribute_tree.value, children = [c])
               # print(updated_tree, sample_tag)
                tag = self._condition_applications.insert(condition_application=updated_tree)
                ts.append(tag)

        ##connect sample to condition applications
        query = ("MATCH (s:Sample {tag : $sample_tag}) "
                 "MATCH (ca:ConditionApplication) "
                 "WHERE ca.tag IN $tags "
                 "MERGE (s)-[r:HAS_APPLICATION]->(ca) "
                 "SET r.created_at = timestamp() ")
        
        self._driver.execute_query(query, routing_="w", sample_tag=sample_tag, tags=ts)
        
        
        
    def get_condition_applications(self, tag: str, attribute_tags : List[str] = None, group_by_attribute : bool = False) -> List[str]|List[ConditionApplicationAttributeModel]:
        """Get all condition procedures for a given sample. 
        
        Parameters
        ----------
        tag : str
            The tag of the sample to get the condition procedures for.
        attribute_tags: List[str], optional
            If provided, only condition applications linked to these attribute tags will be returned.
        group_by_attribute : bool, optional
            If True, the results are grouped by attribute and returned as a list of ConditionApplicationAttribute
            
        Returns
        -------
        List[str]|List[ConditionApplicationAttributeModel]
            A list of condition procedure tags. 
            If group_by_attribute is True, a list of ConditionApplicationAttributeModel is returned.
        """
            
        query =  "MATCH (sample:Sample {tag : $tag})-[:HAS_APPLICATION]->(condition:ConditionApplication) " 
        if group_by_attribute:
            query += "MATCH (condition)-[:OF_ATTRIBUTE]->(a:Attribute) "
            if attribute_tags is not None and len(attribute_tags) > 0:
                query += "WHERE a.tag IN $attribute_tags "
            query += "RETURN a.tag as attribute_tag, collect(condition.tag) as condition_application_tags "
        else:
            if attribute_tags is not None and len(attribute_tags) > 0:
                query += "WHERE EXISTS {(condition)-[:OF_ATTRIBUTE]->(a:Attribute) WHERE a.tag IN $attribute_tags} "
            query += "RETURN collect(condition.tag) "
        r = self._driver.execute_query(query, routing_="r", tag = tag, attribute_tags=attribute_tags, result_transformer_=Result.values if group_by_attribute else Result.value)
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
        return  r[0] if len(r) > 0 else None


    def get_sample_tag_by_index_and_submission(self, sample_index : int, submission_tag : str) -> List[str]:
        "Returns a sample tags."
        
        query = (
            "MATCH (s:Sample {sample_index : $sample_index})<-[:HAS_SAMPLE]-(submission:Submission {tag : $submission_tag}) " 
            "RETURN s.tag ORDER BY s.sample_index ASC "
        )
        
        r = self._driver.execute_query(query,routing_="r",result_transformer_=Result.value, sample_index = sample_index, submission_tag = submission_tag)
        return  r[0] if len(r) > 0 else None

    def get_condition_applications_by_sample_for_submission(self, submission_tag : str, join : str = ";", pivot : bool = True, sort_ca_tags : bool = True, return_sample_index : bool = True) -> pd.DataFrame:
        """Get all condition procedures for all samples in a submission, indexed by sample index. 
        
        Parameters
        ----------
        submission_tag : str
            The submission tag to get the condition procedures for.
        join : str, optional
            If provided, multiple condition procedure tags will be joined into a single string using this separator.
        pivot : bool, optional
            If True, the result will be pivoted to have attributes as columns.
        sort_ca_tags : bool, optional
            If True, the condition application tags will be sorted alphabetically before joining.
        return_sample_index : bool, optional
            If True, the DataFrame will be indexed by sample index. If False, it will be indexed by sample tag.
        Returns
        -------
        pd.DataFrame
            A DataFrame with sample indices as index and condition procedures as columns.
            The columns names represent the instance attribute (e.g. att_environment).
            The values are the condition procedure tags. 
            Multiple tags are separated by a semicolon, if join is provided. The tags are sorted alphabetically if sort_ca_tags is True.
            Pivot is applied if pivot is True, leading to attribute_tags as column names. 
            
        """
        
        query = (
            "MATCH (submission:Submission {tag : $submission_tag})-[:HAS_SAMPLE]->(s:Sample)-[:HAS_APPLICATION]->(ca:ConditionApplication)-[:OF_ATTRIBUTE]->(a:Attribute) "
            "WHERE coalesce(s.excluded, false) = false "
            "RETURN s.sample_index as sample_index, s.tag as sample_tag, a.tag as attribute_tag, collect(ca.tag) as condition_tags "
            "ORDER BY s.sample_index ASC "
        )
        df = self._driver.execute_query(query, routing_="r", result_transformer_=Result.to_df, submission_tag=submission_tag)
        if return_sample_index:
            df.set_index("sample_index", inplace=True)
        else:
            df.set_index("sample_tag", inplace=True)
        if join is not None:
            if sort_ca_tags:
                df["condition_tags"] = df["condition_tags"].apply(lambda x: join.join(sorted(x)))
            else:
                df["condition_tags"] = df["condition_tags"].apply(lambda x: join.join(x))
            if pivot:
                df = df.pivot_table(index=df.index, columns="attribute_tag", values="condition_tags", aggfunc='first')
        return df

    
        # add useGetSampleGenotype
    
    def get_genotypes_by_sample_for_submission(self, submission_tag : str, join : str = ";", pivot : bool = True, sort_ca_tags : bool = True, return_sample_index : bool = True) -> pd.DataFrame:
        """Get all genotypes for all samples in a submission, indexed by sample index. 
        
        Parameters
        ----------
        submission_tag : str
            The submission tag to get the genotypes for.
        join : str, optional
            If provided, multiple genotype tags will be joined into a single string using this separator.
        pivot : bool, optional
            If True, the result will be pivoted to have attributes as columns.
        sort_ca_tags : bool, optional
            If True, the genotype tags will be sorted alphabetically before joining.
        return_sample_index : bool, optional
            If True, the DataFrame will be indexed by sample index. If False, it will be indexed by sample tag.
        Returns
        -------
        pd.DataFrame
            A DataFrame with sample indices as index and genotypes as columns.
            The columns names represent the instance attribute (e.g. att_genotype).
            The values are the genotype tags. 
            Multiple tags are separated by a semicolon, if join is provided. The tags are sorted alphabetically if sort_ca_tags is True.
            Pivot is applied if pivot is True, leading to attribute_tags as column names. 
            
        """
        
        query = (
            "MATCH (submission:Submission {tag : $submission_tag})-[:HAS_SAMPLE]->(s:Sample)-[:HAS_GENOTYPE]->(g:Genotype) "
            "WHERE coalesce(s.excluded, false) = false "
            "RETURN s.sample_index as sample_index, s.tag as sample_tag, 'att_genotype' as attribute_tag, collect(g.tag) as condition_tags "
            "ORDER BY s.sample_index ASC "
        )
        df = self._driver.execute_query(query, routing_="r", result_transformer_=Result.to_df, submission_tag=submission_tag)
        if return_sample_index:
            df.set_index("sample_index", inplace=True)
        else:
            df.set_index("sample_tag", inplace=True)
        if join is not None:
            if sort_ca_tags:
                df["condition_tags"] = df["condition_tags"].apply(lambda x: join.join(sorted(x)))
            else:
                df["condition_tags"] = df["condition_tags"].apply(lambda x: join.join(x))
            if pivot:
                df = df.pivot_table(index=df.index, columns="attribute_tag", values="condition_tags", aggfunc='first')
        return df
    
    def get_sample_genotype(self, tag : str) -> List[str] :
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
        "MATCH (s:Sample {tag: $tag})-[:HAS_GENOTYPE]->(g:Genotype) "
        "RETURN collect(g.tag) AS genotype_tag"
        )


    #     genotype = self._driver.execute_query(query, tag=tag, routing_="r")
    #     return genotype

        r = self._driver.execute_query( query,
                                        routing_="r",
                                        result_transformer_=Result.value,
                                        tag=tag
                                    )
        return r[0] if len(r) > 0 and r[0] is not None else []

    def has_sample_genotype(self, submission_tag : str) -> bool:
        """Check if any sample in the submission has a genotype annotation.

        Parameters
        ----------
        submission_tag : str
            The tag of the submission to check for genotype annotations.

        Returns
        -------
        bool
            True if at least one sample in the submission has a genotype annotation, False otherwise.
        """

        query = (
            "MATCH (submission:Submission {tag: $submission_tag})-[:HAS_SAMPLE]->(s:Sample)-[:HAS_GENOTYPE]->(g:Genotype) "
            "RETURN count(g) > 0 AS has_genotype"
        )

        r = self._driver.execute_query( query,
                                        routing_="r",
                                        result_transformer_=Result.value,
                                        submission_tag=submission_tag
                                    )
        return r[0] if len(r) > 0 else False


    def handle_comparison(self, submission_tag : str, ca_tag_left : str, ca_tag_right : str , within_attribute_tags : str, within_ca_tags : str, annotation_tag : str):
        
        condition_applications = self.get_condition_applications_by_sample_for_submission(submission_tag=submission_tag, sort_ca_tags=True, return_sample_index=False)  #preload condition applications
        if self.has_sample_genotype(submission_tag=submission_tag):
            genotypes = self.get_genotypes_by_sample_for_submission(submission_tag=submission_tag, sort_ca_tags=True, return_sample_index=False)  #preload genotypes
            condition_applications = condition_applications.join(genotypes, how="outer")
        
        if self._genotypes.exists(tag = ca_tag_left):
            attribute_tag = "att_genotype"
        else:
            if ";" in ca_tag_left:
                attribute_tag = self._condition_applications.get_attribute(ca_tag_left.split(";")[0])
            else:
                attribute_tag = self._condition_applications.get_attribute(ca_tag_left)
        if attribute_tag not in condition_applications.columns:
            raise ValueError(status_code=404, detail=f"Attribute tag {attribute_tag} not found in sample condition applications for submission {submission_tag}.")
        
        # if within_trait_tag is not None:
        sample_tags_left = condition_applications[condition_applications[attribute_tag] == ca_tag_left].index
        sample_tags_right = condition_applications[condition_applications[attribute_tag] == ca_tag_right].index

        if within_attribute_tags and within_ca_tags:
            within_attr_list = within_attribute_tags.split(";")
            within_ca_list = within_ca_tags.split(";")
            for within_attr, within_ca in zip(within_attr_list, within_ca_list):
                if within_attr in condition_applications.columns:
                    mask = condition_applications[within_attr] == within_ca
                    sample_tags_left = sample_tags_left[sample_tags_left.isin(condition_applications[mask].index)]
                    sample_tags_right = sample_tags_right[sample_tags_right.isin(condition_applications[mask].index)]

        ##ugly find better way for this.
        if ";" in ca_tag_left: 
            ca_tags = ca_tag_left.split(";") 
            ca_left_text = ",".join([self._condition_applications.get_text(ca_tag) if attribute_tag != "att_genotype" else self._genotypes.get_text(ca_tag) for ca_tag in ca_tags])
        else:
            ca_left_text = self._condition_applications.get_text(ca_tag_left) if attribute_tag != "att_genotype" else self._genotypes.get_text(ca_tag_left)
        
        if ";" in ca_tag_right:
            ca_tags = ca_tag_right.split(";") 
            ca_right_text = ",".join([self._condition_applications.get_text(ca_tag) if attribute_tag != "att_genotype" else self._genotypes.get_text(ca_tag) for ca_tag in ca_tags])
        else:   
            ca_right_text = self._condition_applications.get_text(ca_tag_right) if attribute_tag != "att_genotype" else self._genotypes.get_text(ca_tag_right)

        def clean_ca_text(text):
            if text is None:
                return text
            # remove parentheses containing empty values 
            cleaned = re.sub(r'\(\s*[^)]*\)', lambda m: m.group() if any(c.isdigit() for c in m.group()) else '', text)
            return cleaned.strip()

        ca_left_text = clean_ca_text(ca_left_text)
        ca_right_text = clean_ca_text(ca_right_text)
        sample_tags = sample_tags_left.to_list() + sample_tags_right.to_list()

        suffix = f"{ca_left_text} vs. {ca_right_text}"
        if within_ca_tags:
            within_texts = []
            for t in within_ca_tags.split(";"):
                if t and self._genotypes.exists(tag=t):
                    within_texts.append(self._genotypes.get_text(t) or t)
                elif t:
                    within_texts.append(self._condition_applications.get_text(t) or t)
            if within_texts:
                suffix += f" (within {', '.join(within_texts)})"
    # add within ca tag text
        if annotation_tag is not None:
            annotation_text = self._annotations.get_text(tag=annotation_tag)
            suffix += f" ({annotation_text if annotation_text else annotation_tag})"
        return sample_tags_left, sample_tags_right, sample_tags, suffix, ca_left_text, ca_right_text, attribute_tag

    def calculate_test_quantification_distribution(self, submission_tag : str, testParam : Dict, quantification_type : Literal["protein_groups","precursors"], annotation_tag : str = None) -> Dict:
        """Calculates the quantification distribution for a given submission and quantification type based on a statistical test. This is used to calculate the distribution for the test results in the volcano plot."""
        
        boolIdx = None
       
        sample_tags_left, sample_tags_right, sample_tags, suffix, ca_left_text, ca_right_text, attribute_tag = self.handle_comparison(
            submission_tag=submission_tag, 
            ca_tag_left=testParam["ca_tag_left"],
            ca_tag_right=testParam["ca_tag_right"], 
            within_attribute_tags=testParam.get("within_attribute_tags", None), 
            within_ca_tags=testParam.get("within_ca_tags", None), 
            annotation_tag=testParam.get("annotation_tag", None)
        )
        
        query = (
            "MATCH (submission:Submission {tag: $submission_tag})-[:HAS_SAMPLE]->(s:Sample)-[r:QUANTIFIED]->(pg:ProteinGroup) "
            "WHERE s.tag IN $sample_tags "
            "RETURN pg.tag as feature_tag, r.value as value, s.tag as sample_tag "
        )
        
        r = self._driver.execute_query(query, routing_="r", result_transformer_=Result.to_df, sample_tags=sample_tags, submission_tag=submission_tag)
        
        df = r.pivot_table(index="feature_tag", columns="sample_tag", values="value")
        log2FC = df[sample_tags_left].mean(axis=1) - df[sample_tags_right].mean(axis=1)
        if annotation_tag is not None:
            proteinTags = self._annotations.get_protein_tags(tag=annotation_tag, submission_tag=submission_tag)
            boolIdx = log2FC.index.isin(proteinTags)
                    
        desc = log2FC.describe()
        q = {
                "submission_tag" : submission_tag,
                "suffix" : suffix,
                "annotation_tag" : annotation_tag,
                "distributions" : [QuantileModel(
                        tag = suffix,
                        min = desc["min"],
                        max = desc["max"],
                        m = desc["50%"],
                        q25 = desc["25%"],
                        q75 = desc["75%"],
                        N = desc["count"]
            )]}
        
        if boolIdx is not None:
            log2FCAnnotation = log2FC[boolIdx]
            descAnnotation = log2FCAnnotation.describe()
            q["distributions"].append(QuantileModel(
                tag = f"{suffix} - annotated with {annotation_tag}",
                min = descAnnotation["min"],
                max = descAnnotation["max"],
                m = descAnnotation["50%"],
                q25 = descAnnotation["25%"],
                q75 = descAnnotation["75%"],
                N = descAnnotation["count"]
            ))
        
        return q
        
        

    def insert_proteins(self, submission_tag: str, sample_name: str, protein_tags: List[str]):
        """Insert proteins quantified in a given sample of a submission.

        Parameters
        ----------
        submission_tag : str
            The submission tag associated with the sample.
        sample_name : str
            The name of the sample.
        protein_tags : List[str]
            A list of protein tags to insert as quantified in the sample.

        Raises
        ------
        ValueError
            If the sample does not exist.
        """
        
        sample_tag = self._get_sample_tag(sample_name, submission_tag)

        if not self.exists(tag=sample_tag):
            raise ValueError("Sample does not exist.")

        query = (
            "MATCH (submission:Submission {tag: $submission_tag})"
            "-[:HAS_SAMPLE]->(s:Sample {tag: $sample_tag}) "
            "UNWIND $protein_tags AS ptag "
            "MERGE (p:Protein {tag: ptag}) "
            "MERGE (s)-[:QUANTIFIED]->(p)"
        )

        self._driver.execute_query(
            query,
            routing_="w",
            submission_tag=submission_tag,
            sample_tag=sample_tag,
            protein_tags=protein_tags
        )

    # def update(self, tag: str, text: str = None, genotype_tag: str = None, condition_applications: List[AttributeTree] = None, replicate: int = None) -> bool:
    #     """Update the sample information for a given sample tag."""
    #     if not self.exists(tag):
    #         raise ValueError("Sample does not exist.")

    #     if text is not None:
    #         query = (
    #             "MATCH (s:Sample {tag: $tag}) "
    #             "SET s.text = $text "
    #         )
    #         self._driver.execute_query(query, routing_="w", tag=tag, text=text)

    #     if genotype_tag is not None:
    #         query = (
    #             "MATCH (s:Sample {tag: $tag}) "
    #             "OPTIONAL MATCH (s)-[r:HAS_GENOTYPE]->(:Genotype) "
    #             "DELETE r "
    #             "WITH s "
    #             "MATCH (g:Genotype {tag: $genotype_tag}) "
    #             "MERGE (s)-[:HAS_GENOTYPE]->(g)"
    #         )
    #         self._driver.execute_query(query, routing_="w", tag=tag, genotype_tag=genotype_tag)

    #     if condition_applications is not None:
    #         delete_query = (
    #             "MATCH (s:Sample {tag: $tag})-[r:HAS_APPLICATION]->(:ConditionApplication) "
    #             "DELETE r"
    #         )
    #         self._driver.execute_query(delete_query, routing_="w", tag=tag)
    #         self.insert_condition_application(sample_tag=tag, sample_data=condition_applications)

    #     if replicate is not None:
    #         query = (
    #             "MATCH (s:Sample {tag: $tag}) "
    #             "SET s.replicate = $replicate "
    #         )
    #         self._driver.execute_query(query, routing_="w", tag=tag, replicate=replicate)

    #     return True

    def update(self, tag: str, data: SampleUpdateModel) -> bool:
        """Update the sample information for a given sample tag."""
        if not self.exists(tag):
            raise ValueError("Sample does not exist.")

        if data.text is not None:
            query = (
                "MATCH (s:Sample {tag: $tag}) "
                "SET s.text = $text "
            )
            self._driver.execute_query(query, routing_="w", tag=tag, text=data.text)

        if data.genotype_tag is not None:
            query = (
                "MATCH (s:Sample {tag: $tag}) "
                "OPTIONAL MATCH (s)-[r:HAS_GENOTYPE]->(:Genotype) "
                "DELETE r "
                "WITH s "
                "MATCH (g:Genotype {tag: $genotype_tag}) "
                "MERGE (s)-[:HAS_GENOTYPE]->(g)"
            )
            self._driver.execute_query(query, routing_="w", tag=tag, genotype_tag=data.genotype_tag)

        if data.condition_applications is not None:
            delete_query = (
                "MATCH (s:Sample {tag: $tag})-[r:HAS_APPLICATION]->(:ConditionApplication) "
                "DELETE r"
            )
            self._driver.execute_query(delete_query, routing_="w", tag=tag)
            self.insert_condition_application(sample_tag=tag, sample_data=data.condition_applications)

        if data.replicate is not None:
            query = (
                "MATCH (s:Sample {tag: $tag}) "
                "SET s.replicate = $replicate "
            )
            self._driver.execute_query(query, routing_="w", tag=tag, replicate=data.replicate)

        return True


    def insert_genotype(self, sample_tags: List[str], genotype_tag: str) -> bool:
        """Set the genotype for a given sample.

        Parameters
        ----------
        sample_tags : List[str]
            The tags of the samples to set the genotype for.
        genotype_tag : str
            The tag of the genotype to set for the samples.

        Returns
        -------
        bool
            True if the update was successful, False otherwise.
        """

        query = (
            "UNWIND $sample_tags AS sample_tag "
            "MATCH (s:Sample {tag: sample_tag}) "
            "WITH s "
            "MATCH (g:Genotype {tag: $genotype_tag}) "
            "MERGE (s)-[:HAS_GENOTYPE]->(g)"
        )

        self._driver.execute_query(
            query,
            routing_="w",
            sample_tags=sample_tags,
            genotype_tag=genotype_tag
        )

        return True



    def get_replicate(self, tag: str) -> int:
        query = (
            "MATCH (s:Sample {tag: $tag}) "
            "RETURN s.replicate as replicate"
        )
        r = self._driver.execute_query(query, tag=tag, routing_="r", result_transformer_=Result.value)
        return r[0] if len(r) > 0 else None

    def set_replicate(self, tag: str, replicate: int) -> bool:
        query = (
            "MATCH (s:Sample {tag: $tag}) "
            "SET s.replicate = $replicate "
            "RETURN s.replicate"
        )
        self._driver.execute_query(query, tag=tag, replicate=replicate, routing_="w")
        return True
    
    def get_sample_list(self, submission_tag: str) -> pd.DataFrame:
        # Get all samples ordered by index
        order_query = (
            "MATCH (submission:Submission {tag: $submission_tag})-[:HAS_SAMPLE]->(s:Sample) "
            "RETURN s.text as sample_name, s.sample_index as sample_index "
            "ORDER BY s.sample_index ASC "
        )
        order_df = self._driver.execute_query(
            order_query, routing_="r",
            result_transformer_=Result.to_df,
            submission_tag=submission_tag
        )
        
        # Get condition applications per sample
        ca_query = (
            "MATCH (submission:Submission {tag: $submission_tag})-[:HAS_SAMPLE]->(s:Sample) "
            "-[:HAS_APPLICATION]->(ca:ConditionApplication)-[:OF_ATTRIBUTE]->(a:Attribute) "
            "RETURN s.text as sample_name, a.tag as attribute_tag, "
            "collect(ca.tag) as condition_tags "
        )
        ca_df = self._driver.execute_query(
            ca_query, routing_="r",
            result_transformer_=Result.to_df,
            submission_tag=submission_tag
        )
        
        # Add date prefix to sample names
        today_string = datetime.today().strftime('%Y%m%d')
        prefixed_sample_names = [
            f"{today_string}_{name}" if not name.split('_')[0].isdigit() or len(name.split('_')[0]) != 8 
            else name 
            for name in order_df["sample_name"].tolist()
        ]
        
        if ca_df.empty:
            return pd.DataFrame(index=prefixed_sample_names)
        
        ca_df["condition_tags"] = ca_df["condition_tags"].apply(lambda x: " ".join(sorted(x)))
        pivot = ca_df.pivot_table(
            index="sample_name", 
            columns="attribute_tag", 
            values="condition_tags", 
            aggfunc="first"
        )
        pivot.index.name = None
        pivot.columns.name = None
        # Strip attribute prefix from trait tags for cleaner run names
        for col in pivot.columns:
            pivot[col] = pivot[col].apply(
                lambda x: "_".join([t.split(":")[-1] for t in x.split(" ")]) if x else x
            )
        
        # Create mapping from old names to prefixed names
        name_mapping = dict(zip(order_df["sample_name"].tolist(), prefixed_sample_names))
        pivot = pivot.rename(index=name_mapping)
        
        # Reindex to include all samples in correct order
        return pivot.reindex(prefixed_sample_names, fill_value="")
    
    def set_excluded(self, tag: str, excluded: bool) -> bool:
        "Sets whether a sample is excluded from statistical analysis. Marks the parent submission's cached statistics as outdated."
        query = (
            "MATCH (submission:Submission)-[:HAS_SAMPLE]->(s:Sample {tag : $tag}) "
            "SET s.excluded = $excluded "
            "SET submission.stats_outdated = true "
            "RETURN s.excluded "
        )
        r = self._driver.execute_query(query, routing_="w", tag=tag, excluded=excluded, result_transformer_=Result.value)
        return r[0] if len(r) > 0 else False
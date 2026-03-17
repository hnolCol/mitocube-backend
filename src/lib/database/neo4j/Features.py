from neo4j import Driver, Result 
from typing import List, Dict, Literal
import pandas as pd 

from lib.database.abstract.Features import FeaturesABC 

from config.settings.proteomes.annotations import UniprotAnnotationSettings

from config.models.annotations.feature import FeatureModel
from config.models.calculations.quantile import QuantileModel 

from services.annotations.uniprot import download_proteome_annotations
from config.models.feature import FeatureNeoModel, FeatureSequenceResponseModel



class Neo4JFeatures(FeaturesABC):
    
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
    
    def get(self, tag : str) -> FeatureNeoModel:
        ""
        query = (
            "MATCH (p:Protein) "
            "WHERE p.tag in $tags "
            "RETURN properties(p) as props " 
        )
        r = self._driver.execute_query(query, tag = tag, routing_="r", result_transformer_=Result.value)
        if len(r): raise ValueError("Tag does not exist in the database.")
        return FeatureNeoModel(**r[0])
    
       
    def get_correlated_features(self, 
                                tag : str,
                                annotation_tags : List[str] = None,  
                                submission_tags : List[str] = None,
                                direction : Literal["positive","negative","both"] = "both", 
                                limit : int = None, 
                                feature_type : Literal["protein_group", "peptide"] = "protein_group",
                                min_data_points : int = 20) -> pd.DataFrame:
        """Correlates a feature to all other features 
        by its feature_tag in the submissions given by 'tags' . 

        Parameters
        ----------
        tags : List[stt] - List of submissions 
        feature_tag : str
            the feature tag. 

        Returns
        -------
        pd.DataFrame
            Correlation analysis with the following columns
                - tag (str) - feature_tag that the given tag was correlated to 
                - pearson (float) - the pearson correlation coefficient 
                - N (int) - The number of data points used to calculate the statistics 
                - t (float) - The t-value
        """
        ## extend to multiple submission tags ? MATCH (submission:Submission )-[:HAS_SAMPLE]-(s:Sample) WHERE submission.tag in $submission_tags 
        
        annotation_tags_exists = annotation_tags is not None and len(annotation_tags) > 0
        submission_tags_exists = submission_tags is not None and len(submission_tags) > 0
        if feature_type == "protein_group":   
            query = "MATCH (p_target:ProteinGroup {tag : $tag})<-[rp1:QUANTIFIED]-(s:Sample)-[rp2:QUANTIFIED]->(p:ProteinGroup) "
        elif feature_type == "peptide":
            query = "MATCH (p_target:Peptide {tag : $tag})<-[rp1:QUANTIFIED]-(s:Sample)-[rp2:QUANTIFIED]->(p:Peptide) "
        
        if submission_tags_exists or annotation_tags_exists:
            query += "WHERE "
        
        if annotation_tags_exists:
            if feature_type == "protein_group":
                query += "EXISTS {(p)-[:HAS_PROTEINS]->(protein:Protein)<-[:ANNOTATES]-(annotation:Annotation) WHERE annotation.tag in $annotation_tags} "
        
        if submission_tags_exists:
            if annotation_tags_exists:
                query += " AND "    
            query += " EXISTS {(s)<-[:HAS_SAMPLE]-(submission:Submission) WHERE submission.tag in $submission_tags} "
        
        query += (
            "WITH collect(rp2.value) as x, collect(rp1.value) as y, p "
            "WITH apoc.coll.zip(x, y) AS pairs, apoc.coll.avg(x) AS meanX, apoc.coll.avg(y) AS meanY, x ,y, p "
            "WHERE size(x) > $min_data_points - 1 AND size(y) > $min_data_points - 1 "
            "WITH "
            "   [p IN pairs | (p[0] - meanX) * (p[1] - meanY)] AS products, "
            "   [v IN x | (v - meanX)^2] AS xSquaredDiffs, "
            "   [v IN y | (v - meanY)^2] AS ySquaredDiffs, p, size(pairs) as N "
            "WITH "
            "    apoc.coll.sum(products) / "
            "   (SQRT(apoc.coll.sum(xSquaredDiffs)) * SQRT(apoc.coll.sum(ySquaredDiffs))) AS pearson, p, N "
            "RETURN p.tag as tag, round(pearson,2) as pearson, N as N,  pearson * SQRT(N-2) / SQRT(1-pearson^2) as t " 
        )
        if limit is not None:
            if direction == "both": 
                query += "ORDER BY abs(pearson) DESC LIMIT $limit "
            elif direction == "negative":
                query += "ORDER BY pearson ASC LIMIT $limit "
            elif direction == "positive":
                query += "ORDER BY pearson DESC LIMIT $limit "    
        print(query)
        r = self._driver.execute_query(query, 
                                       routing_="r", 
                                       result_transformer_=Result.to_df, 
                                       min_data_points = min_data_points, 
                                       annotation_tags = annotation_tags, 
                                       submission_tags = submission_tags,
                                       limit = limit, 
                                       tag = tag)
        return r 
    
    
    def count_samples_quantifying_protein(self, tags : List[str]) -> pd.DataFrame:
        
        query = (
            "MATCH (p:Protein)<-[:QUANTIFIED]-(s:Sample) "
            "WHERE p.tag in $tags "
            "RETURN p.tag as tag, count(s) as n_samples "
        )
        
        df = self._driver.execute_query(query, tags = tags, result_transformer_=Result.to_df)
        return df.set_index("tag")
    
    def is_quantified(self, tags : List[str]) -> pd.DataFrame:
        ""
        query = (
            "MATCH (p:Protein) "
            "WHERE p.tag in $tags "
            "MATCH (p)<-[r:QUANTIFIED]-(s:Sample)<-[:HAS_SAMPLE]->(submission:Submission) "
            "WITH count(submission) as N, p, count(rsample) as nsample "
            "RETURN p.tag as tag,  N > 0 as quantified, N as quant_dataset, nsample as quant_samples "
        )
            
        r = self._driver.execute_query(query,routing_="r",result_transformer_=Result.to_df, tags = tags)
        return r 
    
    def exists(self, tag: str) -> bool:
        
        query = (
            "WITH EXISTS {(p:ProteinGroup|Peptide|Protein {tag : $tag})} as exists "
            "RETURN exists"
        )
        
        r = self._driver.execute_query(query,routing_="r",result_transformer_=Result.value, tag = tag)
        return r[0]
    
    def get_unique_quantification_in_genotype(self) -> pd.DataFrame:
        "Get proteins that are exclusively quantified in a single genotype." 
        
        query = (
            "MATCH (p:Protein)<-[:QUANTIFIED]-(s:Sample)-[:HAS_GENOTYPE]->(g:Genotype) "
            "WHERE NOT EXISTS { "
            "    MATCH (p)<-[:QUANTIFIED]-(s2:Sample)-[:HAS_GENOTYPE]->(g2:Genotype) "
            "        WHERE g2.tag <> g.tag "
            "       } "
            "RETURN p.tag as tag, g.tag as genotype_tag, COLLECT(s.tag) AS samples, count(s) as n_samples "
            )
        
        r = self._driver.execute_query(query, routing_="r", result_transformer_=Result.to_df)
        
        print(r)
        return r 

    def get_quantification_stats(self, tags : List[str], submission_tags : List[str] = None) -> pd.DataFrame: 
        """Counts the total number of quantifications
        as well as the number of samples in which the protein 
        could also have been detected (e.g. same proteome).

        Parameters
        ----------
        tag : str
            The feature tag 

        Returns
        -------
        pd.DataFrame
            Counts of the quantification of a particular protein as a
            pandas data frame given the following columns:
                - tag (str) : the feature tag
                - n (int) : The number of samples that quantified the feature 
                - total (int) : The number of total samples that could potentially quantify the sample
                (e.g. samples that are analysed using the same proteome.)
                - submissions (List[str]) : Submission tags in which the protein has been quantified. 
        """
        
        query = (
            "MATCH (p:Protein)-[:IN_PROTEOME]-(:AttributeValue)-[:HAS_ATTRIBUTE_VALUE]-(submission:Submission)-[:HAS_SAMPLE]-(sample:Sample) "
            "WHERE p.tag in $tags "
            )
        
        if submission_tags is not None:
            query += "AND submission.tag in submission_tags"
        
        query += (
            "WITH collect(sample) as all_samples_proteome, p, "
            "[submission IN collect(DISTINCT submission) WHERE (submission)-[:HAS_SAMPLE]-(:Sample)-[:QUANTIFIED]->(p) | submission.tag] as submissions "
            "RETURN p.tag as tag, SIZE(all_samples_proteome) as total, SIZE([sample IN all_samples_proteome WHERE (sample)-[:QUANTIFIED]->(p)]) as n, submissions"
            ""
        )
    
        r = self._driver.execute_query(query, routing_="r", result_transformer_=Result.to_df, tags = tags, submission_tags = submission_tags)
        return r 
        
    def get_protein_sequence(self, tags : str) -> List[FeatureSequenceResponseModel]:
        """
        Returns the protein sequence.
        """
        
        cypher_query = (
            "MATCH (p:Protein) "
            "WHERE p.tag in $tags "
            "MATCH (p)-[:HAS_SEQUENCE]-(s:Sequence) "
            "RETURN p.tag as feature_tag, s.content as sequence"
        ) 
        
        try:
            r, _, _ = self._driver.execute_query(cypher_query,
                                database_="neo4j", 
                                routing_="r",
                                tags = tags)
            
        except Exception as e:
            print("Finding sequence resulted in an error " + str(e))
            return []
        return [sequence.data() for sequence in r]
        
        
    def get_protein_by_tags(self, tags : List[str], as_data_frame : bool = True) -> List[FeatureModel]|pd.DataFrame:
        """
        Returns the protein features by a list of tags. 
        Tags that are not in the database are ignored. 
        
        Parameters
        ----------
        tags : List[str]
            List of feature tags that should be returned. Notably, tags that are missing
            are simply ignored. 
        as_data_frame : bool, optional 
            If the features should be returned as a dataframe. 
        
        
        Returns
        -------
        List[FeatureModel]|pd.DataFrame
            The features in a list of FeatureModel or in a dataframe. The dataframe 
            then has the column names of the params in the FeatureModel and the index
            of the pandas dataframe is the protein tag.
        """
        query = (
            "MATCH (p:Protein) "
            "WHERE p.tag in $tags "
            "RETURN properties(p) " 
        )
        r = self._driver.execute_query(query, tags = tags, database_="neo4j", routing_="r", result_transformer_=Result.value)
        if as_data_frame:
            if len(r) == 0: return pd.DataFrame()
            return pd.DataFrame([ri for ri in r]).set_index("tag")
        
        return [FeatureNeoModel(**ri) for ri in r]

    def get_proteome(self, tags : List[str]) -> pd.DataFrame:
        ""
        query = (
            "MATCH (p:Protein)-[:IN_PROTEOME]->(trait:AttributeValue) "
            "WHERE p.tag in $tags "
            "RETURN p.tag as tag, trait.tag as proteome_tag "
        ) 
        df = self._driver.execute_query(query, routing_="r", result_transformer_=Result.to_df,  tags = tags)
        return df.set_index("tag")
        
    def get_data(self, tags : List[str], submission_tags : List[str] = None, limit : int = 1) -> List[Dict]:
        ""
        if submission_tags is None and limit is None:
            base_submission_query = (
                "MATCH (submission:Submission)-[:HAS_SAMPLE]->(s:Sample)-[:QUANTIFIED_IN]->(p:Protein) "
                "WHERE p.tag in $tags "
                "WITH collect(DISTINCT submission.tag) as filteredSubmissions "
            )
        elif submission_tags is not None and limit is None:
            base_submission_query = (
                "MATCH (p:Protein)<-[r:QUANTIFIED]-(sample:Sample)<-[:HAS_SAMPLE]-(submission:Submission) "
                "WHERE p.tag in $tags AND submission.tag in $submission_tags "
                "WITH collect(DISTINCT submission.tag) as filteredSubmissions "
                )
        elif submission_tags is not None and limit is not None: #if submission tags is given and limit 
            base_submission_query = (
                "MATCH (submission:Submission) "
                "WHERE submission.tag in $submission_tags "
                "WITH collect(DISTINCT submission.tag)[0..$limit] as filteredSubmissions "
            )
        else:
            base_submission_query = (
                "MATCH (submission:Submission)-[:HAS_SAMPLE]->(s:Sample)-[:QUANTIFIED_IN]->(p:Protein)  "
                "WHERE p.tag in $tags "
                "WITH collect(DISTINCT submission.tag)[0..$limit] as filteredSubmissions "
            )
            

   # // Now use these filtered submissions in both parts of the UNION
        query = (
            base_submission_query +
            "CALL { " #call is required to make filteredSubmission available for UNION
            "WITH filteredSubmissions "
            "MATCH (p:Protein)<-[r:QUANTIFIED]-(sample:Sample)<-[:HAS_SAMPLE]-(submission:Submission) "
            "WHERE p.tag IN $tags AND submission.tag IN filteredSubmissions "
            "MATCH (sample)-[:HAS_SAMPLE_ATTRIBUTE_VALUE]->(av:AttributeValue)<-[hav:HAS_ATTRIBUTE_VALUE]-(submission) "
            "RETURN p.tag AS tag, r.value AS value, submission.tag AS submission_tag, "
            "sample.index AS sample_index, hav.attribute_tag AS attribute_tag, "
            "av.tag AS attribute_value_tag "

            "UNION "
            #get the genotypes in the second union statement. 
            "WITH filteredSubmissions "
            "MATCH (p:Protein)<-[r:QUANTIFIED]-(sample:Sample)<-[:HAS_SAMPLE]-(submission:Submission) "
            "WHERE p.tag IN $tags AND submission.tag IN filteredSubmissions "
            "MATCH (sample)-[rhg:HAS_GENOTYPE]->(g:Genotype) "
            "RETURN p.tag AS tag, r.value AS value, submission.tag AS submission_tag,  "
            "sample.index AS sample_index, rhg.attribute_tag AS attribute_tag, "
            "g.tag AS attribute_value_tag "
            "} "
            "RETURN tag, value, submission_tag, sample_index, attribute_tag, attribute_value_tag "
            )
            
           
            
        r = self._driver.execute_query(query,
                                       routing_="r", 
                                       result_transformer_=Result.to_df, 
                                       tags = tags, 
                                       limit = limit,
                                       submission_tags = submission_tags)
        return r 
        
    def get_abundance_distribution(self, tag : str, attribute_tag : str = None) -> List[QuantileModel]:
        "" 
        
        if attribute_tag is not None:
            #  query = (
            #     "MATCH (p:Protein)-[r:QUANTIFIED]-(sample:Sample)-[:HAS_SAMPLE_ATTRIBUTE_VALUE]->(av:AttributeValue)-[:HAS_VALUE]-(a:Attribute) "
            #     "WHERE p.tag = $tag AND a.tag = $attribute_tag "
            #     "RETURN av.tag as trait_tag,apoc.agg.percentiles(r.value, [0,0.25,0.5,0.75,1.0]) as quantiles, count(r) as N, collect(r.value) as values "
            # )
             
             query = (
                #match first the sample attributes and then the dataset attributes.
            "MATCH (p:Protein)<-[r:QUANTIFIED]-(sample:Sample) WHERE p.tag = $tag "
            "MATCH (a:Attribute) WHERE a.tag = $attribute_tag "
            "OPTIONAL MATCH (sample)-[:HAS_SAMPLE_ATTRIBUTE_VALUE]->(av:AttributeValue)<-[:HAS_VALUE]-(a) "
            "OPTIONAL MATCH (sample)<-[:HAS_SAMPLE]-(:Submission)-[:HAS_ATTRIBUTE_VALUE]->(avDataset:AttributeValue)<-[:HAS_VALUE]-(a) "
            "WHERE (av IS NOT NULL AND avDataset IS NULL) OR (av IS NULL AND avDataset IS NOT NULL) "
            "WITH r, COALESCE(av, avDataset) AS avFinal "
            "WHERE avFinal IS NOT NULL "
            "RETURN avFinal.text as text, apoc.agg.percentiles(r.value, [0,0.25,0.5,0.75,1.0]) as quantiles, count(r) as N "
             
             )
             
        else:
            query = (
                "MATCH (p:Protein)-[r:QUANTIFIED]-(sample:Sample)"
                "WHERE p.tag = $tag "
                "RETURN apoc.agg.percentiles(r.value, [0,0.25,0.5,0.75,1.0]) as quantiles, count(r) as N, p.gene_name as text"
            )
        
        
        r = self._driver.execute_query(query, routing_="r", result_transformer_=Result.data, tag = tag, attribute_tag = attribute_tag)
        if not isinstance(r,list): return []
        
        return [QuantileModel(
            text = ri["text"],
            min = ri["quantiles"][0], 
            q25 = ri["quantiles"][1], 
            m = ri["quantiles"][2],
            q75 = ri["quantiles"][3],
            max = ri["quantiles"][4], 
            N = ri["N"] ) for ri in r]
        
    def get_avg_abundance(self, tags: List[str], submission_tags: List[str] = None) -> pd.DataFrame:
        "Neo4J implementation to retrieve the average abundance"
        query = ("MATCH (p:Protein)-[r:QUANTIFIED_IN]->(submission:Submission) "
                 "WHERE p.tag in $tags ")
        
        if submission_tags is not None:
            query += "AND submission.tag in $submission_tags "
            
        query += "RETURN p.tag as tag, r.avg_log2_abundance as value, submission.tag as submission_tag"

        r = self._driver.execute_query(query, 
                                   routing_="r",
                                   tags = tags, 
                                   submission_tags = submission_tags, 
                                   result_transformer_= Result.to_df)
        
        return r 
    
    def get_quantification_per_sample(self, tag : str, submission_tags : List[str] = None) -> pd.DataFrame:
        """Returns the quantification values for a feature per sample. 

        Parameters
        ----------
        tag : str
            The feature tag 
        submission_tags : List[str], optional
            Submission tags that should be considered (e.g. if a filtering is applied). If None
            all datasets will be considered, by default None

        Returns
        -------
        pd.DataFrame
            The quantification values per sample as a pandas data frame with the following columns:
                - value (float) : The quantification value
                - sample_index(int): The sample index
                - submission_tag(str) : The submission tag in which the feature has been quantified.
                - sample_tag(str) : The tag of the sample
                - tag(str) : The tag of the feature
        """
        query = (
            "MATCH (f:ProteinGroup|Peptide {tag : $tag})<-[r:QUANTIFIED]-(s:Sample)<-[:HAS_SAMPLE]-(submission:Submission) "
        )
        if submission_tags is not None and len(submission_tags) > 0:
            query += "WHERE submission.tag in $submission_tags "
        query += "RETURN r.value as value, s.sample_index as sample_index, submission.tag as submission_tag, s.tag as sample_tag, f.tag as tag "
        r = self._driver.execute_query(query, routing_="r", result_transformer_=Result.to_df, tag = tag, submission_tags = submission_tags)
        return r
    
    
    def get_f_value(self, tags: List[str], submission_tags: List[str] = None) -> pd.DataFrame:
        "Neo4J Implementation"
        query = ("MATCH (p:Protein)-[r:QUANTIFIED_IN]->(submission:Submission) "
                 "WHERE p.tag in $tags ")
        
        if submission_tags is not None:
            query += "AND submission.tag in $submission_tags "
            
        query += "RETURN p.tag as tag, r.F as F, submission.tag as submission_tag"

        r = self._driver.execute_query(query, 
                                   routing_="r",
                                   tags = tags, 
                                   submission_tags = submission_tags, 
                                   result_transformer_= Result.to_df)
        
        return r 
    
        
    def get_regulation_summary(self, tags : List[str], submission_tags : List[str] = None) -> pd.DataFrame:
        
        query = "MATCH (p:Protein)-[r:QUANTIFIED_IN]->(submission:Submission) "
        if submission_tags is None:
            query += "WHERE p.tag in $tags "
        else:
            query += "WHERE p.tag in $tags AND submission.tag in $submission_tags"
        
        query += "RETURN p.tag as tag, submission.tag as submission_tag, r.F as F, r.avg_log2_abundance as avg_abundance, SIZE(r.qs) as n"
        
        r = self._driver.execute_query(query,tags=tags,submission_tags=submission_tags,routing_="r",result_transformer_=Result.to_df)

        return r 
    
    
    def get_pairwise_feature_quant(self, feature_tag_x : str, feature_tag_y : str) -> pd.DataFrame:
        "Returns the the quantitifacation of two features from the same sample. Intended to be used for showing correlations. "

        query = (
            "MATCH (p_x:ProteinGroup|Peptide {tag : $feature_tag_x}), (p_y:ProteinGroup|Peptide {tag : $feature_tag_y}) "
            "MATCH (p_x)<-[r_x:QUANTIFIED]-(s:Sample)-[r_y:QUANTIFIED]->(p_y) "
            "RETURN r_x.value as x, r_y.value as y, s.tag as sample_tag "
        )
        
        r = self._driver.execute_query(query,
                                       result_transformer_=Result.to_df,
                                       routing_="r",
                                       feature_tag_x = feature_tag_x, 
                                       feature_tag_y = feature_tag_y
                                       )
        print(r)
        return r 
   
    def get_protein_tags(self, proteome_tags : str|List[str] = "UP000005640", is_quantified : bool = True) -> List[str]:
        """Returns the proteins in the database using the proteome_tags. This 
        should be used when to check for proteins that are actually quantified in any dataset.  
        TODO: MOVE THIS TO PROTEOME CLASS ?
        Parameters
        ----------
        proteome_tags : str | List[str], optional
            _description_, by default "UP000005640"
        is_quantified : bool, optional
            If True only proteins that were quantified in at least on experiment will be returned.
            If False all protein tags will be returned, by default True

        Returns
        -------
        List[str]
            The protein tags (Uniprot IDs)
        """
        if isinstance(proteome_tags,str):
            proteome_tags = [proteome_tags]
        
        if is_quantified:
            cypher_query = (
                "MATCH (p:Protein) "
                "WHERE p.proteome_id in $proteome_tags AND EXISTS {(p)-[:QUANTIFIED_IN]->(:Submission)}"
                "RETURN collect(p.tag)" 
            )
        else:
            cypher_query = (
                "MATCH (p:Protein) "
                "WHERE p.proteome_id in $proteome_tags "
                "RETURN collect(p.tag)" 
            )
        try:
            r = self._driver.execute_query(cypher_query , 
                                        database_="neo4j", 
                                        routing_="r", 
                                        proteome_id = proteome_tags,
                                        result_transformer_= Result.value
                                        )
        except Exception as e:
            print("Query finding resulted in an error " + str(e))
            return []

        return r
    
    def get_quantification_count(self, tags : List[str]):
        """Returns the number of samples that quantified a specific 
        feature. 
        Parameters
        ----------
        tag : str
            The feature tag. (Uniprot ID)
        """
        
        query = (
            "MATCH (p:Protein) "
            "WHERE p.tag in $tags "
            "MATCH (p)<-[:QUANTIFIED]-(s:Sample) "
            "RETURN p.tag as tag, count(s) as N "
        )
        
        r = self._driver.execute_query(query,tags=tags,routing_="r",result_transformer_=Result.data)
        print(r)
        return r 
    
    
    def get_quant_stats(self, tags : List[str]) -> pd.DataFrame:
        """Returns the general stats of a list of features by their tag. 
        
        This includes the following stats:
        
        - quantified_in (int): The number of datasets in which 
        the protein has been quantified 
        - total_number (int): The number of dataset of the same proteome
        - abundance_quantiles (List[float]): The quantiles of the log2 intensity of the requested tag (n=3, 0.25, 0.5, 0.75 quantile)
        - total_abundance_quantiles (List[float]) - The quantiles of all the datasets that used the same proteome (e.g. same organism) 
        (n=4, min, 0.25, 0.5, 0.75, max). 

        Parameters
        ----------
        tags : List[str]
            The tags of the proteins/feature for which the quantification stats should be returned. 
            If the protein is not in the database, it will simply be ignored. 
        """
        
        query = (
            "MATCH (p:Protein) "
            "WHERE p.tag in $tags "
            "MATCH (p)-[:IN_PROTEOME]->(av:AttributeValue) "
            "MATCH (p)-[r_quant:QUANTIFIED_IN]->(d) "
            "WITH p.tag as tag, count(r_quant) as quantified_in, count(d) as total_number, apoc.agg.percentiles(r_quant.avg_log2_abundance, [0.25,0.5,0.75]) as abundance_quantiles, "
            "apoc.coll.zip(collect(r_quant.variance),collect(r_quant.max_variance_attribute)) as variances "
            "MATCH (d:Dataset)-[:HAS_ATTRIBUTE_VALUE]-(av) "
            "MATCH (d)<-[r_all:QUANTIFIED_IN]-(pp:Protein) "
            "RETURN tag, quantified_in, total_number, abundance_quantiles, apoc.agg.percentiles(r_all.avg_log2_abundance, [0,0.25,0.5,0.75,1.0]) as total_abundance_quantiles, variances"
        )
        
        
        r = self._driver.execute_query(query, tags = tags, routing_="r", result_transformer_=Result.to_df)
        print(r)
        
    def get_proteins_by_view(self, limit: int = 10, filter_tag : str = None) -> List[FeatureNeoModel]:
        
        
        if filter_tag is not None:
            
            query = (
                "MATCH (p:Protein)-[:PART_OF]->(f:Filter) "
                "WHERE f.tag = $filter_tag "
            )
        else:   
            query = (
                "MATCH (p:Protein) " 
            )
            
        query += "RETURN properties(p) ORDER BY p.viewed DESC LIMIT $limit"
        
        r = self._driver.execute_query(query,
                                       limit=limit, 
                                       routing_="r",
                                       result_transformer_=Result.value)

        return [FeatureNeoModel(**f) for f in r]
        
    def find(self, search_string : str, limit : int = 10) -> List[str]:
        """Returns a list of features that are found by a query string. 

        Parameters
        ----------
        query : str, optional
            _description_, by default "FB"
        proteome_id : str|List[str], optional
            The proteome_ids (Uniprot), by default "UP000005640" (Human)

        Returns
        -------
        List[FeatureNeoModel]
            The list of features in the database that match the query.
            The list has a maximum length of limit. 
        """
        
        
        query = ("MATCH (p:Protein)-[:HAS_PEPTIDE]->(peptide:Peptide) "
                 "WHERE toLower(p.s) CONTAINS toLower($query_string) OR toLower(peptide.tag) CONTAINS toLower($query_string) OR toLower(p.gene_name) CONTAINS toLower($query_string) "
                 "WITH p.tag as tag, collect(peptide.tag) as peptides, p "
                 "RETURN tag, peptides ORDER BY p.viewed DESC ")

        if limit is not None:
            query += "LIMIT $limit"
            
            
        r = self._driver.execute_query(query, 
                                       routing_="r", 
                                       result_transformer_= Result.values,
                                       query_string = search_string,
                                       limit = limit)
        
        print(r)
        
        # if proteome_tags is None:
        #     cypher_query = (
        #         "MATCH (p:Protein) "
        #         "WHERE p.s CONTAINS $query_string "
        #         "RETURN properties(p) LIMIT $limit" 
        #     )
            
        # else:
        #     if isinstance(proteome_tags,str):
        #         proteome_id = [proteome_id]
        #     cypher_query = (
        #         "MATCH (p:Protein) "
        #         "WHERE p.s CONTAINS $query_string AND p.proteome_tag in $proteome_tags "
        #         "RETURN properties(p) LIMIT $limit" 
        #     )

  
        # try:
        #     r = self._driver.execute_query(cypher_query, 
        #                                 database_="neo4j", 
        #                                 routing_="r", 
        #                                 result_transformer_= Result.value,
        #                                 query_string = query.lower(),
        #                                 proteome_tags = proteome_tags,
        #                                 limit = limit)
        # except Exception as e:
        #     print("Query finding resulted in an error " + str(e))
        #     return []
        # return [FeatureNeoModel(**f) for f in r]
               
        
    def variance(self, tags : List[str], submission_tags : List[str] = None) -> pd.DataFrame:
        """Returns the variance of the quantification of a feature in a list of submissions."""
        
        query = (
            "MATCH (p:Protein)-[r:QUANTIFIED]->(sample:Sample)<-[:HAS_SAMPLE]->(submission:Submission) "
            "WHERE p.tag in $tags "
        )
        
        if submission_tags is not None:
            query += "AND submission.tag in $submission_tags "
            
        
        query += (
            "MATCH (sample)-[:HAS_APPLICATION]->(ca:ConditionApplication) "
            "RETURN p.tag as tag, ca.tag as condition_application_tag, avg(r.value) as std, size(sample) as n_samples, size(submission) as n_submissions "
        )
        
        r = self._driver.execute_query(query, 
                                       routing_="r", 
                                       tags = tags, 
                                       submission_tags = submission_tags, 
                                       result_transformer_=Result.to_df)
    # def find_datasets(self, tags : List[str], filter_tag : str = None) -> pd.DataFrame:
    # put in dataasets 
    #     "Finds the dataset in which the feature is quantified."
        
    #     if filter_tag is None:
    #         query = (
    #             "MATCH (p:Protein) "
    #             "WHERE p.tag in $tags "
    #         )
    #     else:
    #         query = (
    #             "MATCH (f:Filter {tag : $filter_tag})<-[:PART_OF]-(p:Protein)-[:QUANTIFIED_IN]->(submission:Submission) "
    #             "WHERE p.tag in $tags "
    #         )
        
    #     query += "RETURN p.tag as tag, submission.tag as submission_tags"


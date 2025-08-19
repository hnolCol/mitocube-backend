from typing import List, Dict
from neo4j import Driver, Result
import pandas as pd 

from lib.database.abstract.Peptides import PeptidesABC
from lib.database.abstract.Samples import SamplesABC
from config.settings.proteomes.annotations import UniprotAnnotationSettings

from services.annotations.uniprot import download_proteome_annotations
from config.models.feature import FeatureNeoModel
from config.models.performance import QCPeptidesModel, QCPeptideModel
from config.models.peptides import PeptideResponseModel

class Neo4JPeptides(PeptidesABC):
     
    def __init__(self, driver : Driver, samples : SamplesABC) -> None:
        ""
        self._driver = driver 
        self._samples = samples 
        
        
    def _insert_peptides(self, data : pd.DataFrame) -> int:
        """Inserts peptides into the database.
        
        Parameters
        ----------
        data : pd.DataFrame
            DataFrame containing peptide data with columns 'sequence', 'protein_tag', 'start', 'end'.
        
        Returns
        -------
        int
            The number of peptides inserted.
        """
        if data.empty:
            return 0

        if not all(column in data.columns for column in ['sequence', 'protein_tag', 'start', 'end']):
            raise ValueError("DataFrame must contain 'sequence', 'protein_tag', 'start', and 'end' columns.")   

        query = (
            "UNWIND $data as peptide "
            "MERGE (p:Peptide {tag : peptide.tag}) "
            "SET p.sequence = peptide.sequence, p.start = peptide.start, p.end = peptide.end, created_at = timestamp() "
            "WITH p, peptide "
            "MATCH (prot:Protein {tag : peptide.protein_tag}) "
            "MERGE (p)<-[:HAS_PEPTIDE]-(prot) "
            "RETURN count(p) as count"
        )
        
        r = self._driver.execute_query(query, data=data.to_dict(orient="records"), routing_="w", result_transformer_=Result.value)
        print(r)
        return r[0]
    
    
    def correlate_to(self, tag : str, min_size : int = 4, limit : int = None, filter_tag : str = None, exclude_within_protein_correlation : bool = True) -> pd.DataFrame:
        """Correlates a peptide to all other peptides based on their quantification data.
        
        Parameters
        ----------
        tag : str
            The tag of the peptide to correlate with others.
        min_size : int, optional
            Minimum size of the peptide quantification data to consider for correlation, by default 4.
        limit : int, optional
            Maximum number of results to return, by default None (no limit).
        filter_tag : str, optional
            If provided, only peptides of proteins that are part of the filter_tag will be considered for correlation.
        exclude_within_protein_correlation : bool, optional
            If True, excludes correlations between peptides of the same protein, by default True.

        Returns
        -------
        pd.DataFrame
            DataFrame containing the correlation results.
                Headers:
                - peptide1: The tag of the first peptide.
                - peptide2: The tag of the second peptide.
                - pearson_corr: The Pearson correlation coefficient between the two peptides.
                - protein1: The tag of the first protein.
                - protein2: The tag of the second protein.
                - size: The number of quantification data points used for the correlation.
        """
        
        if not self.exists(tag=tag):
            raise ValueError(f"Peptide with tag {tag} does not exist.")
        
        query = (
                "MATCH (prot1:Protein)-[:HAS_PEPTIDE]->(p1:Peptide {tag: $tag})<-[r1:QUANTIFIED]-(s:Sample)-[r2:QUANTIFIED]->(p2:Peptide)<-[:HAS_PEPTIDE]-(prot2:Protein) "
            )
        
        
        if exclude_within_protein_correlation and filter_tag is None:
            query += "WHERE prot1.tag <> prot2.tag "
            
        elif filter_tag is not None:
            query += "WHERE EXISTS {(prot1)-[PART_OF]->(Filter {tag : $filter_tag})<-[:PART_OF]-(prot2)} AND prot1.tag <> prot2.tag "
            if exclude_within_protein_correlation:
                query += "AND prot1.tag <> prot2.tag "
            
        query += (
            "WITH p1, p2, collect(r1.value) as v1, collect(r2.value) as v2, prot1, prot2 "
            "WHERE size(v1) > $min_size AND size(v2) > $min_size "
            "WITH p1, p2, gds.similarity.pearson(v1, v2) as pearson_corr, prot1 as protein1, prot2 as protein2, size(v1) as size "
            "RETURN p1.tag as peptide1, p2.tag as peptide2, pearson_corr, protein1.tag as protein1, protein2.tag as protein2, size "
            "ORDER BY pearson_corr DESC "
        )
        
        if limit is not None:
            query += "LIMIT $limit "

        r = self._driver.execute_query(query, tag=tag, min_size=min_size, limit=limit, routing_="r", result_transformer_=Result.data)
        return pd.DataFrame(r)
    
    def correlate_peptides_of_proteins(self, protein_tags: List[str], min_size : int = 4, limit : int = None) -> pd.DataFrame:
        """Correlates peptides within a list of proteins based on their quantification data.
        Only peptides with sufficient quantification data are considered for correlation and only peptides of the 
        same protein are correlated. 
        
        Parameters
        ----------
        protein_tags : List[str]
            List of protein tags to correlate peptides for.
        min_size : int, optional
            Minimum size of the peptide quantification data to consider for correlation, by default 4.
        limit : int, optional
            Maximum number of results to return, by default None (no limit).
        Returns
        -------
        pd.DataFrame
            DataFrame containing the correlation results.
        """
        query = (
            "MATCH (p:Protein) "
            "WHERE p.tag IN $protein_tags "
            "WITH p "
            "MATCH (p)-[:HAS_PEPTIDE]->(pep:Peptide) "
            "WITH p, collect(pep) as peptides "
            "UNWIND peptides as p1 "
            "UNWIND peptides as p2 "
            "WITH p, p1, p2 WHERE p1.tag <> p2.tag "
            "MATCH (p1)<-[r1:QUANTIFIED]-(s:Sample)-[r2:QUANTIFIED]->(p2) "
            "WITH p, p1, p2, collect(r1.value) as v1, collect(r2.value) as v2 "
            "WHERE size(v1) > $min_size AND size(v2) > $min_size "
            "WITH p, p1, p2, gds.similarity.pearson(v1, v2) as pearson_corr, size(v1) as size "
            "RETURN p1.tag as peptide1, p2.tag as peptide2, pearson_corr, p.tag as protein_tag, size as n "
            "ORDER BY pearson_corr DESC "
        )
        if limit is not None:
            query += "LIMIT $limit "

        r = self._driver.execute_query(query, protein_tags=protein_tags, routing_="r", result_transformer_=Result.values, min_size=min_size, limit=limit)

        return pd.DataFrame(r, columns=["peptide1_tag","peptide2_tag", "pearson_correlation", "protein_tag", "size"])
        
    def exists(self, tag: str) -> bool:
        query = (
            "WITH EXISTS {(p:Peptide {tag : $tag})} as peptide_exists "
            "RETURN peptide_exists "
        )    
        r = self._driver.execute_query(query, tag = tag, result_transformer_=Result.value)
        return r[0]


    def find(self, search_string: str, limit: int = None) -> List[str]:
        """Finds all peptides matching the search string.

        Parameters
        ----------
        search_string : str
            The search string to match against peptide sequences.
        limit : int, optional
            The maximum number of results to return. If None, all matching peptides are returned.
        Returns
        -------
        List[str]
            A list of matching peptide tags (e.g. the sequence).
        """
        
        query = (
            "MATCH (p:Peptide) "
            "WHERE p.tag CONTAINS $search_string "
            "RETURN p.tag "
        )
        if limit is not None:
            query += "LIMIT $limit "

        r = self._driver.execute_query(query, search_string=search_string.lower(), limit=limit, result_transformer_=Result.value, routing_="r")
        return [ri for ri in r]
    
    def get(self, tag: str) -> PeptideResponseModel:
        """Returns a peptide by its tag (sequence).

        Parameters
        ----------
        tag : str
            The peptide tag (sequence).

        Returns
        -------
        PeptideResponseModel
            The peptide model.
        """
        
        query = (
            "MATCH (p:Peptide {tag : $tag})"
            "WITH EXISTS {(p)<-[:QUANTIFIED]-(s:Sample)} as quantified, p "
            "RETURN p.tag as tag, p.sequence as sequence, p.start as start, p.end as end, quantified"
        )
        
        r = self._driver.execute_query(query, tag=tag, routing_="r", result_transformer_=Result.value)
        
        if not r:
            raise ValueError(f"Peptide with tag {tag} not found.")
        
        return PeptideResponseModel(**r[0])
    
    def get_abundance(self, tag: str, submission_tags: List[str] = None) -> pd.DataFrame:
        """Retrieves the abundance data of a peptide by its tag.

        Parameters
        ----------
        tag : str
            The tag of the peptide to retrieve.
        submission_tags : List[str], optional
            A list of submission tags to filter the abundance data by, by default None (all submissions).

        Returns
        -------
        pd.DataFrame
            DataFrame containing the abundance data of the peptide.
                Headers:
                - sample_tag: The tag of the sample.
                - value: The abundance value of the peptide in the sample.
                - submission_tag: The tag of the submission.
        
        Raises
        ------
        ValueError
            If the peptide with the given tag does not exist.
        """
        
        if not self.exists(tag=tag):
            raise ValueError(f"Peptide with tag {tag} does not exist.")
        
        query = "MATCH (p:Peptide {tag : $tag})<-[r:QUANTIFIED]-(s:Sample)<-[:HAS_SAMPLE]-(sub:Submission)"
        
        if submission_tags is not None:
            query += " WHERE sub.tag IN $submission_tags} "
        query += "RETURN p.tag as peptide_tag, s.tag as sample_tag, sub.tag as submission_tag, r.value as value"
        
        r = self._driver.execute_query(query, tag=tag, submission_tags=submission_tags, result_transformer_=Result.to_df, routing_="r")
        if r.empty:
            raise ValueError(f"No abundance data found for peptide with tag {tag}.")
        return r 


    def get_abundance_by_condition_application(self, tag : str, condition_application_tag: str, submission_tags: List[str] = None, attribute_tag : str = None) -> pd.DataFrame:
        """Retrieves the abundance data of a peptide by its condition application tag.

        Parameters
        ----------
        tag : str 
            The tag of the peptide to retrieve.
        condition_application_tag : str
            The tag of the condition application to retrieve.
        submission_tags : List[str], optional
            A list of submission tags to filter the abundance data by, by default None (all submissions).
        attribute_tag : str, optional
            The tag of the attribute to filter the abundance data by, by default None (all attributes). If given, 
            the condition application must have an attribute with this tag. 

        Returns
        -------
        pd.DataFrame
            DataFrame containing the abundance data of the peptide.
                Headers:
                - sample_tag: The tag of the sample.
                - value: The abundance value of the peptide in the sample.
                - submission_tag: The tag of the submission.
        
        Raises
        ------
        ValueError
            If the condition application with the given tag does not exist.
        """
        if not self.exists(tag=tag):
            raise ValueError(f"Peptide with tag {tag} does not exist.")
        
        query = "MATCH (p:Peptide)<-[r:QUANTIFIED]-(s:Sample)-[:HAS_APPLICATION]->(ca:ConditionApplication {tag : $condition_application_tag}) "

        if attribute_tag is not None:
            
            query += "WHERE EXISTS {(ca)-[:OF_ATTRIBUTE]->(a:Attribute {tag = $attribute_tag})} "
            if submission_tags is not None:
                query += "AND s.submission.tag IN $submission_tags "
                
        elif submission_tags is not None:
            
            query += "WHERE sub.tag IN $submission_tags "

        query += "COLLECT(r.value) as values "
        query += "RETURN ca.tag as condition_application_tag, p.tag as peptide_tag, avg(values) as avg_values, stDev(values) as std_dev, count(s) as n_samples "

        r = self._driver.execute_query(query, condition_application_tag=condition_application_tag, submission_tags=submission_tags, routing_="r", result_transformer_=Result.to_df)
        
        if r.empty:
            raise ValueError(f"No abundance data found for condition application with tag {condition_application_tag}.")
        
        return r



    def insert(self, protein_tags: List[str], peptide_sequence: str) -> bool:
        """Inserts a peptide into the database.

        Parameters
        ----------
        protein_tags : List[str]
            The tags of the proteins associated with the peptide.
        peptide_sequence : str
            The amino acid sequence of the peptide.

        Returns
        -------
        bool
            True if the insertion was successful, False otherwise.
        """
        
        query = (
            "MERGE (p:Peptide {tag: $peptide_sequence}) "
            "WITH p "
            "UNWIND $protein_tags as protein_tag "
            "MATCH (prot:Protein {tag: protein_tag}) "
            "MERGE (p)<-[:HAS_PEPTIDE]-(prot) "
            "RETURN count(p) > 0"
        )
        
        r = self._driver.execute_query(query, peptide_sequence=peptide_sequence, protein_tags=protein_tags, routing_="w", result_transformer_=Result.value)
        return r[0]
    
    
    def is_quantified(self, peptide_tag: str) -> bool:
        """Checks if a peptide is quantified.

        Parameters
        ----------
        peptide_tag : str
            The tag of the peptide to check.

        Returns
        -------
        bool
            True if the peptide is quantified, False otherwise.
        """
        
        query = (
            "MATCH (p:Peptide {tag: $peptide_tag})<-[:QUANTIFIED]-(s:Sample) "
            "RETURN COUNT(s) > 0"
        )
        
        r = self._driver.execute_query(query, peptide_tag=peptide_tag, routing_="r", result_transformer_=Result.value)
        return r[0] 
    
    
    def insert_quantification_data_from_df(self, submission_tag: str, sample_name : str, quantification_data: pd.DataFrame) -> int:    
        """Inserts quantification data for multiple peptides for a specific sample.
        Parameters
        ----------
        submission_tag : str
            The tag of the submission to which the quantification data belongs.
        sample_name : str
            The name of the sample for which the quantification data is being inserted.
        quantification_data : pd.DataFrame
            DataFrame containing the quantification data with columns:
                - tag (peptide tag)
                - value (quantification value, log2 intensity).
                - score (score for the identification of the peptide, optional).
                - retention_time (retention time of the peptide, optional).
                
        Returns
        -------
        int
            The number of samples for which the quantification data was successfully inserted.
        
        Raises
        ------
        ValueError
            If the DataFrame does not contain the required columns or if the sample does not exist. 
            If the sample does not exist, no data will be inserted and 0 is returned.
            
        """
        
        if not all(column in quantification_data.columns for column in ['tag', 'value']):
            raise ValueError("DataFrame must contain 'tag' and 'value' columns.")
        quantification_data = quantification_data.dropna() 
        
        if quantification_data.empty:
            return 0   
        if not self._samples.exists(tag=sample_name):
            raise ValueError(f"Sample with tag {sample_name} does not exist.")
        
        sample_tag = self._samples._get_sample_tag(sample_name, submission_tag)
        if not self._samples.exists(tag=sample_tag):
            raise ValueError(f"Sample with tag {sample_tag} does not exist.")
        
        query = (
            "MATCH (s:Submission {tag: $submission_tag})-[:HAS_SAMPLE]->(sample:Sample {tag: $sample_tag}) "
            "UNWIND $quantification_data as data "
            "MATCH (p:Peptide {tag: data.tag}) "
            "MERGE (p)<-[r:QUANTIFIED]-(sample) "
            "SET r.value = data.value, r.created_at = timestamp(), r.score = data.score, r.retention_time = data.retention_time "
            "RETURN COUNT(sample) > 0"
        )
        
        r = self._driver.execute_query(query, 
                                    submission_tag=submission_tag, 
                                    sample_tag=sample_tag,
                                    quantification_data=quantification_data.to_dict(orient="records"), 
                                    routing_="w", 
                                    result_transformer_=Result.value)  
        print(r)
        return r[0] if len(r) > 0 else 0
    
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
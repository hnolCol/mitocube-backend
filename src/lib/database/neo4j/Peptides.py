from typing import List, Dict
from neo4j import Driver, Result
import pandas as pd 

from lib.database.abstract.Peptides import PeptidesABC
from config.settings.proteomes.annotations import UniprotAnnotationSettings

from services.annotations.uniprot import download_proteome_annotations
from config.models.feature import FeatureNeoModel
from config.models.performance import QCPeptidesModel, QCPeptideModel
from config.models.peptides import PeptideResponseModel

class Neo4JPeptides(PeptidesABC):
     
    def __init__(self, driver : Driver) -> None:
        ""
        self._driver = driver  
        
        
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
            "SET p.sequence = peptide.sequence, p.start = peptide.start, p.end = peptide.end "
            "MATCH (prot:Protein {tag : peptide.protein_tag}) "
            "MERGE (p)<-[:HAS]-(prot) "
            "RETURN count(p) as count"
        )
        
        r = self._driver.execute_query(query, data=data.to_dict(orient="records"), routing_="w", result_transformer_=Result.value)
        return r[0]
        
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
            "MERGE (p)<-[:HAS]-(prot) "
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
    
    
    def insert_quantification_data_from_df(self, submission_tag: str, quantification_data: pd.DataFrame) -> int:    
        """Inserts quantification data for multiple peptides."""
        
        query = (
            "MATCH (s:Submission {tag: $submission_tag}) "
            "UNWIND $quantification_data as data "
            "MATCH (p:Peptide {tag: data.peptide_tag}) "
            "MERGE (p)<-[:QUANTIFIED]-(s) "
            "SET s.value = data.value "
            "RETURN COUNT(s) > 0"
        )

    
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